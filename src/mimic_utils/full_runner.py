"""Full-data correctness run for a concept-port attempt, executed on HPC.

This is the gate that decides whether a port is correct.  Everything before it
-- the demo shape gate included -- only earns the right to spend one of these.

The whole run happens inside a single Slurm job, on one node, because both
sides of the comparison already live there:

1. Embedded Pathling (:mod:`mimic_utils.embedded_runner`) preprocesses completed
   derived dependencies, evaluates the attempt's ViewDefinitions and
   ``concept.sql`` over the 156 GB Delta warehouse, and writes
   ``candidate.full.parquet``.
2. :func:`mimic_utils.compare_port_results.compare_full` opens the immutable
   14.5 GB DuckDB oracle **read-only** and runs the keyed row-level diff
   against that Parquet, entirely as DuckDB SQL.

Neither side moves across the network, and rows are never materialised into
Python -- ``vitalsign`` is 9.7M rows.  Only the two small JSON artifacts
(``comparison.full.json``, ``run_meta.full.json``) travel back to the laptop;
the Parquet stays on scratch.

The oracle is **never recomputed**.  It was built once by
``mimic_utils.build_full_oracle`` and is the fixed ground truth; a run that
rebuilt it would be comparing a port against itself.

Gates (see ``mimic-iv/concepts_fhir/LOOP_CONTRACT.md``, which is
authoritative): column schema identity is a hard gate, and so is a declaration
the candidate's own data refutes.  **Row count is not a gate**, and neither is
a value conflict.  FHIR does not carry everything relational MIMIC-IV carries,
*and* it rewrites some of what it does carry, so a faithful port can return
fewer rows and can disagree on values it had no way to reproduce.  Both reach
the judge as ``review``, distinguished by ``divergence.tier``: ``gap_shaped``
needs a named absent element, ``contested`` needs the upstream ETL statement
that rewrote the value.

The verdict is never hand-calculated here; it comes from the comparator, and
this module is careful never to collapse ``review`` onto either ``match`` or
``mismatch`` on its way back to the orchestrator.

Attempt artifacts are write-once, so one attempt carries at most one full run.
A fix is a new attempt.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mimic_utils.compare_port_results import (
    UNREPRESENTABLE_FILENAME,
    compare_full,
    load_unrepresentable,
    write_comparison,
)
from mimic_utils.demo_runner import DemoRunError, _default_manifest, resolve_attempt_dir
from mimic_utils.embedded_runner import (
    EmbeddedExecutor,
    EmbeddedRunError,
    execute_attempt,
    resolve_warehouse,
)

CANDIDATE_NAME = "candidate.full.parquet"
COMPARISON_NAME = "comparison.full.json"
RUN_META_NAME = "run_meta.full.json"

ORACLE_ENV_KEY = "MIMIC_FULL_ORACLE"


class FullRunError(RuntimeError):
    """The full run could not be executed."""


def resolve_oracle(explicit: Optional[str | Path] = None) -> Path:
    """Resolve the full oracle DuckDB path from *explicit* -> env.

    As with the warehouse there is no default: pointing the correctness gate
    at the demo oracle by accident would produce a confidently wrong verdict.
    """
    raw = explicit if explicit is not None else os.environ.get(ORACLE_ENV_KEY)
    if not raw:
        raise FullRunError(
            "No oracle given: pass --oracle or set "
            f"{ORACLE_ENV_KEY}. There is no default -- the demo oracle must "
            "never decide a full-data verdict."
        )
    path = Path(raw).expanduser()
    if not path.is_file():
        raise FullRunError(f"Full oracle not found: {path}")
    return path


@dataclass
class FullRunResult:
    """Everything the full run produced, plus the comparator's verdict."""

    concept: str
    attempt_dir: str
    warehouse: str = ""
    oracle: str = ""
    view_labels: List[str] = field(default_factory=list)
    candidate_path: str = ""
    comparison_path: str = ""
    run_meta_path: str = ""
    columns: List[str] = field(default_factory=list)
    column_types: Dict[str, str] = field(default_factory=dict)
    row_count: Optional[int] = None
    oracle_row_count: Optional[int] = None
    verdict: Optional[str] = None  # match | mismatch | review
    divergence: Dict[str, Any] = field(default_factory=dict)
    diagnostics: List[str] = field(default_factory=list)
    execute_seconds: float = 0.0
    compare_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    @property
    def matched(self) -> bool:
        """True only when nothing diverged at all."""
        return self.verdict == "match" and not self.errors

    @property
    def needs_judge(self) -> bool:
        """True when only gap-shaped divergence remains.

        Deliberately not folded into :attr:`matched`: a `review` is neither a
        pass nor a failure, and a caller that treats it as either is making the
        judge's decision for it.
        """
        return self.verdict == "review" and not self.errors


def run_full(
    concept: str,
    *,
    attempt_dir: Optional[str | Path] = None,
    warehouse: Optional[str | Path] = None,
    oracle: Optional[str | Path] = None,
    manifest_path: Optional[str | Path] = None,
    artifact_root: Optional[str | Path] = None,
    repo_root: Optional[Path] = None,
    attempt: Optional[int] = None,
    schema: str = "mimiciv_derived",
    rtol: float = 0.001,
    atol: float = 1e-9,
    sample_limit: int = 20,
    executor: Optional[EmbeddedExecutor] = None,
) -> FullRunResult:
    """Execute one attempt on full data and compare it against the oracle."""
    try:
        resolved_attempt = resolve_attempt_dir(
            concept,
            attempt_dir=attempt_dir,
            artifact_root=artifact_root,
            attempt=attempt,
        )
    except DemoRunError as exc:
        raise FullRunError(str(exc)) from exc

    result = FullRunResult(concept=concept, attempt_dir=str(resolved_attempt))

    candidate_dir = resolved_attempt / CANDIDATE_NAME
    comparison_path = resolved_attempt / COMPARISON_NAME
    for path in (candidate_dir, comparison_path):
        if path.exists():
            result.errors.append(
                f"{path.name} already exists (attempts are write-once); "
                f"retry the concept to create a new attempt instead of "
                f"re-running this one"
            )
            return result

    manifest = Path(manifest_path) if manifest_path else _default_manifest(repo_root)
    if not manifest.is_file():
        result.errors.append(f"Oracle manifest not found: {manifest}")
        return result

    resolved_warehouse = resolve_warehouse(warehouse)
    resolved_oracle = resolve_oracle(oracle)
    result.warehouse = str(resolved_warehouse)
    result.oracle = str(resolved_oracle)

    # -- 1. execute the port, embedded, and write Parquet -------------------
    started = time.perf_counter()
    owned: Optional[EmbeddedExecutor] = None
    try:
        frame, owned, labels = execute_attempt(
            resolved_attempt,
            warehouse_path=resolved_warehouse,
            executor=executor,
            concept=concept,
            artifact_root=artifact_root,
        )
        result.view_labels = labels
        result.columns = list(frame.columns)
        result.column_types = dict(frame.dtypes)
        # `mode("error")` rather than overwrite: the write-once rule is
        # enforced by the filesystem, not only by the check above.
        frame.write.mode("error").parquet(str(candidate_dir))
    except EmbeddedRunError as exc:
        result.errors.append(str(exc))
        return result
    except Exception as exc:  # noqa: BLE001 - a Spark failure is a real verdict input
        result.errors.append(f"full execution failed: {exc}")
        return result
    finally:
        result.execute_seconds = time.perf_counter() - started
        if owned is not None and executor is None:
            owned.close()

    result.candidate_path = str(candidate_dir)

    # -- 2. keyed diff against the read-only oracle -------------------------
    # DuckDB reads the Spark part-files through a glob; `scan_expression`
    # dispatches on the `.parquet` suffix, which the glob preserves.
    scan_target = str(candidate_dir / "*.parquet")
    started = time.perf_counter()
    try:
        # An attempt may declare columns MIMIC-on-FHIR cannot represent at all.
        # Optional -- most concepts have none -- but when present it is verified
        # against the candidate, not taken on trust.
        declaration_path = resolved_attempt / UNREPRESENTABLE_FILENAME
        declared = (
            load_unrepresentable(declaration_path)
            if declaration_path.is_file()
            else None
        )
        comparison = compare_full(
            concept,
            manifest,
            resolved_oracle,
            scan_target,
            schema=schema,
            rtol=rtol,
            atol=atol,
            sample_limit=sample_limit,
            unrepresentable=declared,
        )
    except Exception as exc:  # noqa: BLE001
        result.errors.append(f"comparison failed: {exc}")
        return result
    finally:
        result.compare_seconds = time.perf_counter() - started

    result.comparison_path = str(write_comparison(comparison, comparison_path))
    result.verdict = comparison.get("verdict")
    result.divergence = dict(comparison.get("divergence") or {})
    result.diagnostics = list(comparison.get("diagnostics") or [])
    row_count = comparison.get("row_count") or {}
    result.row_count = row_count.get("candidate")
    result.oracle_row_count = row_count.get("oracle")

    # -- 3. run metadata ----------------------------------------------------
    result.run_meta_path = str(_write_run_meta(resolved_attempt, result))
    return result


def _write_run_meta(attempt: Path, result: FullRunResult) -> Path:
    """Write ``run_meta.full.json`` write-once beside the comparison."""
    path = attempt / RUN_META_NAME
    if path.exists():
        raise FullRunError(f"{RUN_META_NAME} already exists (write-once): {path}")
    meta = {
        "format_version": "1.0",
        "concept": result.concept,
        "dataset": "full",
        "engine": "pathling-embedded",
        "attempt_dir": result.attempt_dir,
        "warehouse": result.warehouse,
        "oracle": result.oracle,
        "view_labels": result.view_labels,
        "columns": result.columns,
        "column_types": result.column_types,
        "row_count": result.row_count,
        "oracle_row_count": result.oracle_row_count,
        "verdict": result.verdict,
        "divergence": result.divergence,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "timings_seconds": {
            "execute": round(result.execute_seconds, 3),
            "compare": round(result.compare_seconds, 3),
        },
    }
    path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------


def format_full_report(result: FullRunResult, *, color: bool = True) -> str:
    """Render *result* as a human-readable report string."""
    GREEN = "\033[92m" if color else ""
    RED = "\033[91m" if color else ""
    YELLOW = "\033[93m" if color else ""
    RESET = "\033[0m" if color else ""

    lines: List[str] = ["=" * 68]
    lines.append(f"  Full-data run — concept '{result.concept}'")
    lines.append(f"  Attempt:   {result.attempt_dir}")
    lines.append(f"  Warehouse: {result.warehouse or '(unresolved)'}")
    lines.append(f"  Oracle:    {result.oracle or '(unresolved)'}")
    lines.append("=" * 68)
    lines.append("")

    if result.view_labels:
        lines.append(f"  Views registered: {', '.join(result.view_labels)}")
    if result.columns:
        lines.append(f"  Result columns ({len(result.columns)}):")
        for col in result.columns:
            lines.append(f"    {col:<28} {result.column_types.get(col, '?')}")
    if result.row_count is not None:
        lines.append("")
        lines.append(
            f"  Rows: candidate {result.row_count:,} vs "
            f"oracle {result.oracle_row_count:,}  (not a gate)"
        )
    lines.append("")
    lines.append(
        f"  Timings: execute {result.execute_seconds:.1f}s, "
        f"compare {result.compare_seconds:.1f}s"
    )
    if result.candidate_path:
        lines.append(f"  Candidate:  {result.candidate_path}")
    if result.comparison_path:
        lines.append(f"  Comparison: {result.comparison_path}")
    if result.run_meta_path:
        lines.append(f"  Run meta:   {result.run_meta_path}")
    lines.append("")

    if result.matched:
        lines.append(f"  Verdict: {GREEN}MATCH{RESET}")
        lines.append("    Nothing diverged. The judge is not called.")
    elif result.verdict == "review":
        tier = result.divergence.get("tier")
        lines.append(f"  Verdict: {YELLOW}REVIEW ({tier}){RESET}")
        if tier == "contested":
            lines.append(
                "    A value conflict is present. Either a port bug or upstream"
            )
            lines.append(
                "    ETL transformation loss — the data cannot tell you which."
            )
            lines.append(
                "    Still not a failure: the judge decides, at the raised bar."
            )
        elif tier == "attributed":
            attributed = result.divergence.get("attributed") or [{}]
            lines.append(
                "    A value conflict, replayed to a known upstream mimic-fhir ETL"
            )
            lines.append(
                "    cast on every conflicting row — so no port can invert it and"
            )
            lines.append(
                "    there is nothing for a diagnosis to add. Citation(s): "
                + ", ".join(attributed[0].get("citations") or [])
            )
            lines.append(
                "    The judge still rules: it confirms provenance and fraction."
            )
        else:
            lines.append(
                "    Only divergence a MIMIC-on-FHIR coverage gap could explain."
            )
            lines.append("    Not a pass and not a failure — the judge decides.")
        for diag in result.diagnostics:
            lines.append(f"    {YELLOW}?{RESET} {diag}")
    elif result.verdict == "mismatch":
        lines.append(f"  Verdict: {RED}MISMATCH{RESET}")
        lines.append(
            "    A machine-provable contradiction. Nothing to weigh; no judge."
        )
        for diag in result.diagnostics:
            lines.append(f"    {RED}x{RESET} {diag}")
    for err in result.errors:
        lines.append(f"    {RED}x{RESET} {err}")

    lines.append("")
    lines.append("=" * 68)
    if result.matched:
        lines.append(f"  {GREEN}Overall: PASS — concept may be marked done{RESET}")
    elif result.needs_judge:
        lines.append(
            f"  {YELLOW}Overall: REVIEW — spawn the equivalence judge; do NOT "
            f"retry blindly{RESET}"
        )
        if result.divergence.get("judge_bar"):
            lines.append(f"  Bar for an accept: {result.divergence['judge_bar']}")
    else:
        lines.append(f"  {RED}Overall: FAIL — diagnose and retry in a new attempt{RESET}")
    lines.append("=" * 68)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def run_full_cli(args: Optional[List[str]] = None) -> int:
    """Run the full-data correctness gate. Exit 0 on match, 1 otherwise."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Execute a concept-port attempt on full MIMIC-on-FHIR via "
        "embedded Pathling and compare it against the immutable full oracle. "
        "This is the correctness gate: schema identity and the classified "
        "keyed row-level diff. Row count is reported, never gated.",
    )
    parser.add_argument("concept", help="Concept stem (e.g. age).")
    parser.add_argument(
        "--attempt-dir", default=None,
        help="Attempt directory to run (default: the concept's current attempt).",
    )
    parser.add_argument(
        "--attempt", type=int, default=None,
        help="Explicit attempt number instead of the current one.",
    )
    parser.add_argument(
        "--warehouse", default=None,
        help=f"Delta warehouse path (env: MIMIC_FHIR_WAREHOUSE).",
    )
    parser.add_argument(
        "--oracle", default=None,
        help=f"Full oracle DuckDB file, opened read-only (env: {ORACLE_ENV_KEY}).",
    )
    parser.add_argument(
        "--manifest", default=None,
        help="Oracle manifest JSON (default: oracle_manifest.full.json).",
    )
    parser.add_argument("--artifact-root", default=None, help="Artifact root directory.")
    parser.add_argument(
        "--schema", default="mimiciv_derived",
        help="Oracle schema holding the derived concepts.",
    )
    parser.add_argument(
        "--rtol", type=float, default=0.001,
        help="Relative tolerance for floating-point VALUES (never row count).",
    )
    parser.add_argument("--atol", type=float, default=1e-9)
    parser.add_argument("--sample-limit", type=int, default=20)
    parser.add_argument("--no-color", action="store_true")
    opts = parser.parse_args(args)

    try:
        result = run_full(
            concept=opts.concept,
            attempt_dir=opts.attempt_dir,
            attempt=opts.attempt,
            warehouse=opts.warehouse,
            oracle=opts.oracle,
            manifest_path=opts.manifest,
            artifact_root=opts.artifact_root,
            schema=opts.schema,
            rtol=opts.rtol,
            atol=opts.atol,
            sample_limit=opts.sample_limit,
        )
    except (FullRunError, EmbeddedRunError) as exc:
        print(f"full run failed: {exc}")
        return 1

    print(format_full_report(result, color=not opts.no_color))
    if result.matched:
        return 0
    # 2, not 1: a `review` is not a failed run. The Slurm script decides the
    # job's own status by whether a verdict artifact exists, so this code only
    # has to avoid telling a caller that "the judge must look" means "wrong".
    return 2 if result.needs_judge else 1


if __name__ == "__main__":  # pragma: no cover - module entry for the Slurm job
    raise SystemExit(run_full_cli())
