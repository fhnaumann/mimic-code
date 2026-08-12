"""Compare two versions of a concept's SQL on demo data, without touching state.

The question this answers is narrow and worth its own tool: *does this SQL edit
change the answer?*  It is asked before deciding whether an edit is worth a
`reopen` and an HPC run, and it is asked about concepts whose loop state is
finished and must stay that way -- so nothing here transitions a concept, writes
into a real attempt directory, or consumes an attempt number.

**A clean result is not evidence of equivalence.**  The demo cohort is 100
patients; `enzyme`'s divergence is 65 rows in 1.6M, and every DST-gap timestamp
in the corpus lands in a few hundred rows.  A probe that finds nothing has
failed to falsify the edit, which is not the same as confirming it.  What the
probe *can* do is prove an edit semantic for a few seconds of laptop time,
which is worth knowing before spending 10-30 minutes of queue plus runtime.

Read a clean result as "no cheap objection found", and a dirty one as "this is
semantic -- it must go through the loop".
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Sequence

from mimic_utils.conversion_state import ConversionController, StateError

#: Artifacts a copied attempt directory must not carry: the demo runner refuses
#: to overwrite them, and they describe the run we are about to replace.
_RUN_OUTPUTS = ("candidate.demo.parquet", "shape.demo.json")


class CastProbeError(StateError):
    """The probe cannot be run as requested."""


@dataclass
class VariantResult:
    """One side of the comparison."""

    label: str
    sql_path: str
    workdir: str
    executed: bool = False
    verdict: Optional[str] = None
    row_count: int = 0
    columns: list[str] = field(default_factory=list)
    column_types: dict[str, str] = field(default_factory=dict)
    candidate_path: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class ProbeResult:
    """What the two variants did, and whether their outputs agree."""

    concept: str
    baseline: VariantResult
    variant: VariantResult
    schema_differences: list[str] = field(default_factory=list)
    row_count_delta: Optional[int] = None
    differing_columns: dict[str, int] = field(default_factory=dict)
    only_baseline: Optional[int] = None
    only_variant: Optional[int] = None
    compared: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def falsified(self) -> bool:
        """True when the edit demonstrably changes the answer on demo data."""
        return bool(
            self.schema_differences
            or self.differing_columns
            or self.row_count_delta
            or self.only_baseline
            or self.only_variant
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "compared": self.compared,
            "falsified": self.falsified,
            "schema_differences": self.schema_differences,
            "row_count_delta": self.row_count_delta,
            "only_baseline": self.only_baseline,
            "only_variant": self.only_variant,
            "differing_columns": self.differing_columns,
            "notes": self.notes,
            "baseline": vars(self.baseline),
            "variant": vars(self.variant),
        }

    def format(self) -> str:
        lines = [f"Cast probe: {self.concept}", "=" * 70]
        for side in (self.baseline, self.variant):
            state = "ok" if side.executed else "FAILED"
            lines.append(f"  {side.label:<10} {state:<7} {side.row_count:>9,} rows  {side.sql_path}")
            for error in side.errors:
                lines.append(f"      {error}")

        if not self.compared:
            lines.append("")
            lines.append("  Not compared -- see errors above.")
            return "\n".join(lines)

        lines.append("")
        if self.schema_differences:
            lines.append("  Schema differs:")
            for difference in self.schema_differences:
                lines.append(f"    {difference}")
        if self.row_count_delta:
            lines.append(f"  Row count differs by {self.row_count_delta:+,}")
        if self.only_baseline or self.only_variant:
            lines.append(
                f"  Unmatched rows: {self.only_baseline or 0:,} baseline-only, "
                f"{self.only_variant or 0:,} variant-only"
            )
        if self.differing_columns:
            lines.append("  Columns whose own values changed (each compared alone):")
            for column, count in sorted(self.differing_columns.items(), key=lambda kv: -kv[1]):
                lines.append(f"    {column:<28} {count:>9,} rows")

        lines.append("")
        if self.falsified:
            lines.append(
                "  FALSIFIED — this edit is semantic. It changes the answer on 100\n"
                "  patients, so it cannot be applied as a cosmetic in-place fix.\n"
                "  Route it through `mimic_utils reopen <concept> --by human --reason ...`."
            )
        else:
            lines.append(
                "  No difference on demo data.\n"
                "  This is NOT evidence of equivalence — the demo cohort is 100 patients\n"
                "  and the divergences this loop cares about are often <0.01% of rows.\n"
                "  It means no cheap objection was found, nothing more."
            )
        for note in self.notes:
            lines.append(f"  note: {note}")
        return "\n".join(lines)


def _stage_variant(source: Path, destination: Path, sql: Optional[Path]) -> Path:
    """Copy an attempt directory to *destination*, optionally swapping the SQL."""
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)
    for name in _RUN_OUTPUTS:
        stale = destination / name
        if stale.is_dir():
            shutil.rmtree(stale)
        elif stale.exists():
            stale.unlink()
    if sql is not None:
        shutil.copyfile(sql, destination / "concept.sql")
    return destination


def _run_variant(concept: str, label: str, workdir: Path, warehouse: Optional[str]) -> VariantResult:
    from mimic_utils.demo_runner import run_demo

    result = VariantResult(
        label=label,
        sql_path=str((workdir / "concept.sql").resolve()),
        workdir=str(workdir),
    )
    run = run_demo(concept, attempt_dir=workdir, warehouse=warehouse, skip_compare=True)
    result.executed = run.executed
    result.verdict = run.verdict
    result.row_count = run.row_count
    result.columns = list(run.columns)
    result.column_types = dict(run.column_types)
    result.candidate_path = run.candidate_path
    result.errors = list(run.errors)
    return result


def _compare_parquet(
    baseline: VariantResult, variant: VariantResult, result: ProbeResult
) -> None:
    """Full-outer-join the two candidate parquets and name what moved.

    Compares as multisets over every shared column rather than joining on the
    natural key: the question is "did anything change", not "which rows
    correspond". The key *is* available -- `oracle_manifest.full.json` declares
    one per concept -- so a keyed comparison is possible and would report
    matched/only-baseline/only-variant per key instead of the blunter unmatched
    counts below. It is deliberately not done here: this tool answers a yes/no
    falsification question in a few seconds, and `compare_port_results` is the
    loop's real comparator. If you find yourself wanting the keyed answer, you
    want a full run, not a richer probe.
    """
    import duckdb

    shared = [column for column in baseline.columns if column in variant.columns]
    if not shared:
        result.notes.append("no shared columns; nothing to compare")
        return

    quoted = ", ".join(f'"{column}"' for column in shared)

    def glob_literal(path: str) -> str:
        # Inlined rather than bound: DuckDB refuses a prepared parameter inside
        # CREATE VIEW ("Unexpected prepared parameter"). These paths are ours --
        # an attempt directory under the artifact root -- but double the quotes
        # anyway so a directory name can never terminate the literal.
        escaped = f"{path}/**/*.parquet".replace("'", "''")
        return f"'{escaped}'"

    connection = duckdb.connect(":memory:")
    try:
        connection.execute(
            f"CREATE VIEW b AS SELECT {quoted} FROM "
            f"read_parquet({glob_literal(baseline.candidate_path)}, hive_partitioning=false)"
        )
        connection.execute(
            f"CREATE VIEW v AS SELECT {quoted} FROM "
            f"read_parquet({glob_literal(variant.candidate_path)}, hive_partitioning=false)"
        )
        # Multiset difference in both directions. Any row that changed in any
        # column shows up on both sides, which is enough to answer "did this
        # edit change the answer" without needing to pair the residual.
        result.only_baseline = connection.execute(
            "SELECT count(*) FROM (SELECT * FROM b EXCEPT ALL SELECT * FROM v)"
        ).fetchone()[0]
        result.only_variant = connection.execute(
            "SELECT count(*) FROM (SELECT * FROM v EXCEPT ALL SELECT * FROM b)"
        ).fetchone()[0]

        # Per-column attribution, one column at a time as a multiset.
        #
        # This used to hold every OTHER column fixed and diff (others, column),
        # which reports a row for a column whenever any column in the tuple
        # moved -- so a single changed column smeared across all of them. On a
        # one-column timestamp edit it named subject_id, stay_id and icp at 276
        # rows each when only charttime had moved, sending a reader after three
        # columns the edit provably did not touch. False leads are worse than no
        # attribution, so compare each column alone instead.
        #
        # The limitation is the honest one: a multiset diff of a single column
        # cannot see a permutation that preserves the column's value counts.
        # `only_baseline` / `only_variant` above are computed over whole rows and
        # do catch that, so read the two together.
        for column in shared:
            differing = connection.execute(
                f'SELECT count(*) FROM (SELECT "{column}" FROM b '
                f'EXCEPT ALL SELECT "{column}" FROM v)'
            ).fetchone()[0]
            if differing:
                result.differing_columns[column] = differing
        result.compared = True
    finally:
        connection.close()


def probe_cast_change(
    concept: str,
    *,
    variant_sql: str | Path,
    baseline_sql: Optional[str | Path] = None,
    artifact_root: Optional[str | Path] = None,
    scratch_dir: Optional[str | Path] = None,
    warehouse: Optional[str] = None,
) -> ProbeResult:
    """Run *concept* twice on demo data and report what the SQL edit changed.

    *baseline_sql* defaults to the ``concept.sql`` of the concept's current
    attempt -- the query that earned the recorded verdict.  Neither the state
    nor the real attempt directory is modified.
    """
    controller = ConversionController(artifact_root=artifact_root)
    attempt_dir = controller.attempt_dir(concept)
    if attempt_dir is None:
        raise CastProbeError(
            f"'{concept}' has no attempt directory to probe against; the probe "
            f"compares an edit to the SQL a run already produced"
        )

    variant_path = Path(variant_sql).expanduser().resolve()
    if not variant_path.is_file():
        raise CastProbeError(f"Variant SQL not found: {variant_path}")
    baseline_path = Path(baseline_sql).expanduser().resolve() if baseline_sql else None
    if baseline_path is not None and not baseline_path.is_file():
        raise CastProbeError(f"Baseline SQL not found: {baseline_path}")

    scratch = Path(scratch_dir).expanduser() if scratch_dir else attempt_dir.parent / ".cast_probe"
    scratch.mkdir(parents=True, exist_ok=True)

    baseline_result = _run_variant(
        concept, "baseline",
        _stage_variant(attempt_dir, scratch / "baseline", baseline_path),
        warehouse,
    )
    variant_result = _run_variant(
        concept, "variant",
        _stage_variant(attempt_dir, scratch / "variant", variant_path),
        warehouse,
    )

    result = ProbeResult(concept=concept, baseline=baseline_result, variant=variant_result)
    if not (baseline_result.executed and variant_result.executed):
        return result

    # A column present on one side only is already a falsification, and it also
    # makes the row comparison meaningless, so report it and keep going.
    for column in baseline_result.columns:
        if column not in variant_result.columns:
            result.schema_differences.append(f"{column}: present in baseline, missing in variant")
    for column in variant_result.columns:
        if column not in baseline_result.columns:
            result.schema_differences.append(f"{column}: added by variant")
    for column, declared in baseline_result.column_types.items():
        other = variant_result.column_types.get(column)
        if other is not None and other != declared:
            result.schema_differences.append(f"{column}: {declared} -> {other}")

    result.row_count_delta = variant_result.row_count - baseline_result.row_count
    if baseline_result.row_count == 0 and variant_result.row_count == 0:
        result.notes.append(
            "both variants returned 0 rows on demo -- the cohort may hold nothing "
            "for this concept, so the probe proved nothing at all"
        )
        result.compared = True
        return result

    _compare_parquet(baseline_result, variant_result, result)
    return result


def cmd_cast_probe(
    concept: str,
    *,
    variant_sql: str,
    baseline_sql: Optional[str] = None,
    artifact_root: Optional[str] = None,
    scratch_dir: Optional[str] = None,
    warehouse: Optional[str] = None,
    as_json: bool = False,
) -> tuple[str, int]:
    result = probe_cast_change(
        concept,
        variant_sql=variant_sql,
        baseline_sql=baseline_sql,
        artifact_root=artifact_root,
        scratch_dir=scratch_dir,
        warehouse=warehouse,
    )
    # The exit code is the contract, and it must not depend on --json. A caller
    # partitioning concepts on $? has to be able to tell three states apart:
    #
    #   0  compared, no cheap objection found
    #   1  compared, FALSIFIED -- the edit is semantic
    #   2  not compared -- a side failed to execute, or nothing was comparable
    #
    # 2 matters most. Before this, broken SQL and "no difference" both exited 0,
    # so a loop reading $? silently recorded a crash as a clean result.
    if not result.compared:
        code = 2
    elif result.falsified:
        code = 1
    else:
        code = 0
    if as_json:
        return json.dumps(result.to_dict(), indent=2, sort_keys=True), code
    return result.format(), code


__all__ = [
    "CastProbeError",
    "ProbeResult",
    "VariantResult",
    "cmd_cast_probe",
    "probe_cast_change",
]
