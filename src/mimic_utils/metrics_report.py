"""Static HTML rollup of every terminal conversion metrics artifact.

Reads ``mimic-iv/concepts_fhir/metrics/<concept>/run_<NNNN>.json`` (written by
``conversion_metrics``), the conversion DAG (the denominator) and the per-concept
ConversionState, and renders one self-contained ``index.html``.  The report is
regenerated in place: unlike the run artifacts it is *not* write-once.

Bad inputs are skipped and reported in a banner rather than raising; only an
unwritable output path is fatal.
"""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from mimic_utils.conversion_metrics import METRICS_SCHEMA_VERSION, TERMINAL_STATUSES
from mimic_utils.conversion_state import ConversionController, _resolve_artifact_root

METRICS_DIR = "mimic-iv/concepts_fhir/metrics"
REPORT_NAME = "index.html"
RATES_NAME = "rates.json"
RUN_RE = re.compile(r"^run_(\d{4})\.json$")
TOKEN_NAMES = ("input", "output", "reasoning", "cache_read", "cache_write")
COST_INPUT_NAMES = ("input", "cache_read", "cache_write")
COST_OUTPUT_NAMES = ("output", "reasoning")
PORTED_STATUSES = ("COMPLETED", "COMPLETED_WITH_DIVERGENCE")
# A port that predates the metrics tracker: state.json is terminal and ported, but no
# artifact was ever finalized.  Counted as ported so the headline reflects real progress;
# contributes nothing to token, cost or runtime aggregates, because it has nothing.
PORTED_NO_METRICS = "PORTED_NO_METRICS"
STATUS_LABELS = {
    "COMPLETED": "completed",
    "COMPLETED_WITH_DIVERGENCE": "completed w/ divergence",
    "FAILED": "failed",
    "BLOCKED_REPRESENTATION": "blocked (representation)",
    PORTED_NO_METRICS: "ported (no metrics)",
    "IN_PROGRESS": "in progress",
    "NOT_STARTED": "not started",
}
STATUS_CLASSES = {
    "COMPLETED": "ok",
    "COMPLETED_WITH_DIVERGENCE": "warn",
    "FAILED": "bad",
    "BLOCKED_REPRESENTATION": "bad",
    PORTED_NO_METRICS: "pale",
    "IN_PROGRESS": "info",
    "NOT_STARTED": "muted",
}
CLASS_COUNT_NAMES = (
    "identical", "differing_conflict", "differing_null_only", "only_oracle", "only_candidate",
)


class ReportError(OSError):
    """The report could not be written."""


# ---------------------------------------------------------------------------
# Small typed helpers
# ---------------------------------------------------------------------------


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _int(value: Any) -> Optional[int]:
    number = _num(value)
    return None if number is None else int(number)


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _text(value: Any) -> Optional[str]:
    if value is None or isinstance(value, (dict, list)):
        return None
    value = str(value).strip()
    return value or None


def _zero_tokens() -> dict[str, int]:
    return {**{name: 0 for name in TOKEN_NAMES}, "total": 0}


def _add_tokens(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, int]:
    result = {name: int(_num(left.get(name)) or 0) + int(_num(right.get(name)) or 0) for name in TOKEN_NAMES}
    result["total"] = sum(result.values())
    return result


def _read_json(path: Path) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"malformed JSON ({exc.msg} at line {exc.lineno})"
    except OSError as exc:
        return None, f"unreadable ({exc.strerror or exc})"
    return (value, None) if isinstance(value, dict) else (None, "top-level JSON value is not an object")


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


def _load_rates(path: Path) -> tuple[Optional[dict[str, dict[str, float]]], Optional[str]]:
    """Return the pricing table, or ``None`` when costs must be omitted."""
    raw, error = _read_json(path)
    if raw is None:
        return None, f"rates table {path.name} not usable ({error}); cost columns omitted"
    rates: dict[str, dict[str, float]] = {}
    for key, value in raw.items():
        entry = _dict(value)
        input_rate, output_rate = _num(entry.get("input")), _num(entry.get("output"))
        if input_rate is not None and output_rate is not None:
            rates[str(key)] = {"input": input_rate, "output": output_rate}
    if not rates:
        return None, f"rates table {path.name} has no usable entries; cost columns omitted"
    return rates, None


def _rate_key(provider: Any, model: Any) -> str:
    """Pricing key is ``provider + "/" + model``; the variant is not priced."""
    return f"{_text(provider) or 'unknown'}/{_text(model) or 'unknown'}"


def _model_cost(tokens: Mapping[str, Any], rate: Mapping[str, float]) -> float:
    billed_in = sum(_num(tokens.get(name)) or 0.0 for name in COST_INPUT_NAMES)
    billed_out = sum(_num(tokens.get(name)) or 0.0 for name in COST_OUTPUT_NAMES)
    return rate["input"] * billed_in / 1e6 + rate["output"] * billed_out / 1e6


def _new_cost() -> dict[str, Any]:
    return {"value": 0.0, "priced": 0, "unpriced": set()}


def _add_cost(acc: dict[str, Any], other: Mapping[str, Any]) -> dict[str, Any]:
    acc["value"] += float(other["value"])
    acc["priced"] += int(other["priced"])
    acc["unpriced"] |= set(other["unpriced"])
    return acc


def _price(tokens: Mapping[str, Any], key: str, rates: Optional[Mapping[str, Mapping[str, float]]]) -> dict[str, Any]:
    acc = _new_cost()
    if rates is None:
        return acc
    rate = rates.get(key)
    if rate is None:
        acc["unpriced"].add(key)
    else:
        acc["value"], acc["priced"] = _model_cost(tokens, rate), 1
    return acc


def _cost_json(acc: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "value": round(float(acc["value"]), 6),
        "priced": int(acc["priced"]),
        "unpriced": sorted(acc["unpriced"]),
    }


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def _collect_runs(metrics_dir: Path, notes: list[str]) -> dict[str, list[tuple[int, dict[str, Any]]]]:
    runs: dict[str, list[tuple[int, dict[str, Any]]]] = defaultdict(list)
    try:
        concept_dirs = sorted(path for path in metrics_dir.iterdir() if path.is_dir())
    except OSError as exc:
        notes.append(f"Metrics directory {metrics_dir} could not be listed ({exc.strerror or exc})")
        return {}
    for concept_dir in concept_dirs:
        try:
            files = sorted(concept_dir.iterdir())
        except OSError as exc:
            notes.append(f"{concept_dir.name}/: directory could not be listed ({exc.strerror or exc})")
            continue
        for path in files:
            match = RUN_RE.match(path.name)
            if match is None or not path.is_file():
                continue
            label = f"{concept_dir.name}/{path.name}"
            data, error = _read_json(path)
            if data is None:
                notes.append(f"{label}: skipped, {error}")
                continue
            version = data.get("schema_version")
            if version != METRICS_SCHEMA_VERSION:
                notes.append(f"{label}: skipped, schema_version {version!r} != {METRICS_SCHEMA_VERSION!r}")
                continue
            status = data.get("terminal_status")
            if status not in TERMINAL_STATUSES:
                notes.append(f"{label}: skipped, terminal_status {status!r} is not a terminal status")
                continue
            runs[_text(data.get("concept")) or concept_dir.name].append((int(match.group(1)), data))
    return {concept: sorted(values) for concept, values in runs.items()}


def _dag_view(artifact_root: Path, notes: list[str]) -> tuple[Optional[ConversionController], Optional[set[str]]]:
    try:
        controller = ConversionController(artifact_root=artifact_root)
    except Exception as exc:  # noqa: BLE001 - degraded metrics-only view is the contract
        notes.append(f"Conversion DAG unreadable ({exc}); no denominator, metrics-only view")
        return None, None
    return controller, set(controller.dag_concepts)


def _state_status(controller: Optional[ConversionController], concept: str, notes: list[str]) -> Optional[str]:
    if controller is None:
        return None
    try:
        state = controller._read_state(concept)  # noqa: SLF001 - same-package accessor, as in conversion_metrics
    except Exception as exc:  # noqa: BLE001
        notes.append(f"{concept}: ConversionState unreadable ({exc})")
        return None
    return None if state is None else str(state.status)


# ---------------------------------------------------------------------------
# Rollup
# ---------------------------------------------------------------------------


def _agent_models(runs: Sequence[tuple[int, Mapping[str, Any]]]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = defaultdict(set)
    for _, data in runs:
        for entry in _list(_dict(data.get("provenance")).get("agent_model_list")):
            item = _dict(entry)
            agent = _text(item.get("agent")) or "unknown"
            mapping[agent].add(_rate_key(item.get("provider"), item.get("model")))
    return dict(mapping)


def _concept_rollup(
    concept: str,
    runs: Sequence[tuple[int, Mapping[str, Any]]],
    rates: Optional[Mapping[str, Mapping[str, float]]],
) -> dict[str, Any]:
    latest = runs[-1][1]
    comparator, convergence = _dict(latest.get("final_comparator")), _dict(latest.get("convergence"))
    fidelity = _dict(comparator.get("fidelity"))

    tokens, cost, runtime, hpc_seconds = _zero_tokens(), _new_cost(), 0.0, 0.0
    by_agent_tokens: dict[str, dict[str, int]] = defaultdict(_zero_tokens)
    by_agent_seconds: dict[str, float] = defaultdict(float)
    by_agent_messages: dict[str, int] = defaultdict(int)
    by_model: dict[str, dict[str, Any]] = {}
    hpc_jobs: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []

    for number, data in runs:
        run_tokens = _dict(data.get("tokens"))
        tokens = _add_tokens(tokens, run_tokens)
        run_runtime = _dict(data.get("runtime"))
        runtime += _num(run_runtime.get("seconds")) or 0.0
        hpc_seconds += _num(run_runtime.get("hpc_accounted_seconds")) or 0.0
        run_cost = _new_cost()
        for key, entry in _dict(run_tokens.get("by_model")).items():
            item = _dict(entry)
            model_tokens = _dict(item.get("tokens"))
            rate_key = _rate_key(item.get("provider"), item.get("model"))
            _add_cost(run_cost, _price(model_tokens, rate_key, rates))
            slot = by_model.setdefault(str(key), {
                "key": str(key), "provider": _text(item.get("provider")), "model": _text(item.get("model")),
                "variant": _text(item.get("variant")), "rate_key": rate_key,
                "session_count": 0, "tokens": _zero_tokens(),
            })
            slot["session_count"] += _int(item.get("session_count")) or 0
            slot["tokens"] = _add_tokens(slot["tokens"], model_tokens)
        _add_cost(cost, run_cost)
        for agent, entry in _dict(run_tokens.get("by_agent")).items():
            by_agent_tokens[agent] = _add_tokens(by_agent_tokens[agent], _dict(_dict(entry).get("tokens")))
        for agent, entry in _dict(data.get("per_stage")).items():
            stage = _dict(entry)
            by_agent_seconds[agent] += _num(stage.get("duration_seconds")) or 0.0
            by_agent_messages[agent] += _int(stage.get("completed_assistant_messages")) or 0
        for entry in _list(data.get("hpc_jobs")):
            job = _dict(entry)
            hpc_jobs.append({
                "run": number, "attempt": _int(job.get("attempt")),
                "runtime_seconds": _num(job.get("runtime_seconds")),
                "runtime_source": _text(job.get("runtime_source")),
                "accounting_present": bool(job.get("accounting_present")),
            })
        history.append({
            "run": number, "status": _text(data.get("terminal_status")),
            "verdict": _text(_dict(data.get("final_comparator")).get("verdict")),
            "tokens": int(_num(run_tokens.get("total")) or 0),
            "cost": _cost_json(run_cost), "runtime_seconds": _num(run_runtime.get("seconds")) or 0.0,
        })

    models = _agent_models(runs)
    agents = []
    for agent in sorted(set(by_agent_tokens) | set(by_agent_seconds)):
        keys = sorted(models.get(agent, set()))
        agent_cost = _new_cost()
        if len(keys) == 1:
            agent_cost = _price(by_agent_tokens[agent], keys[0], rates)
        elif rates is not None and keys:
            agent_cost["unpriced"] = set(keys)
        agents.append({
            "agent": agent, "tokens": dict(by_agent_tokens[agent]),
            "seconds": round(by_agent_seconds[agent], 3),
            "messages": by_agent_messages[agent],
            "models": keys, "cost": _cost_json(agent_cost),
        })

    attempts = []
    for entry in _list(_dict(latest.get("per_attempt")).get("attempts")):
        item = _dict(entry)
        item_convergence = _dict(item.get("convergence"))
        full, demo = _dict(item_convergence.get("full")), _dict(item_convergence.get("demo"))
        attempts.append({
            "attempt": _int(item.get("attempt")),
            "full_verdict": _text(full.get("verdict")), "full_tier": _text(full.get("tier")),
            "demo_verdict": _text(demo.get("verdict")),
            "hpc_job_submitted": bool(item_convergence.get("hpc_job_submitted")),
            "judge_invoked": bool(item_convergence.get("judge_invoked")),
        })

    return {
        "concept": concept,
        "status": _text(latest.get("terminal_status")) or "unknown",
        "state_status": None,
        "in_dag": True,
        "has_metrics": True,
        "runs": len(runs),
        "run_numbers": [number for number, _ in runs],
        "verdict": _text(comparator.get("verdict")),
        "tier": _text(comparator.get("tier")),
        "match": comparator.get("match") if isinstance(comparator.get("match"), bool) else None,
        "identical_fraction": _num(fidelity.get("identical_fraction")),
        "oracle_rows": _int(fidelity.get("oracle_rows")),
        "row_count_match": _dict(fidelity.get("row_count")).get("match"),
        "schema_match": fidelity.get("schema_match"),
        "attempts_total": _int(convergence.get("attempts_total")),
        "judge_invocations": _int(convergence.get("judge_invocations")),
        "convergence": {
            key: convergence.get(key)
            for key in (
                "attempts_total", "judge_invocations", "semantic_rework_cycles", "engineering_counter",
                "hpc_counter", "submitted_jobs", "full_validation_rounds", "divergence_decided_by",
                "human_manual_override",
            )
        },
        "class_counts": {
            name: _int(_dict(comparator.get("class_counts")).get(name))
            for name in CLASS_COUNT_NAMES
            if _dict(comparator.get("class_counts")).get(name) is not None
        },
        "tokens": tokens,
        "cost": _cost_json(cost),
        "runtime_seconds": round(runtime, 3),
        "hpc_seconds": round(hpc_seconds, 3),
        "actual_elapsed_seconds": _num(_dict(latest.get("runtime")).get("actual_elapsed_seconds")),
        "attempts": attempts,
        "hpc_jobs": hpc_jobs,
        "agents": agents,
        "by_model": sorted(by_model.values(), key=lambda item: item["key"]),
        "source_sql_path": _text(_dict(latest.get("provenance")).get("source_sql_path")),
        "history": history,
    }


def _placeholder_status(state_status: Optional[str]) -> str:
    if state_status in PORTED_STATUSES:
        return PORTED_NO_METRICS
    if state_status is not None and state_status not in TERMINAL_STATUSES:
        return "IN_PROGRESS"
    return "NOT_STARTED"


def _placeholder(concept: str, state_status: Optional[str]) -> dict[str, Any]:
    return {
        "concept": concept, "status": _placeholder_status(state_status),
        "state_status": state_status, "in_dag": True, "has_metrics": False,
        "runs": 0, "run_numbers": [], "verdict": None, "tier": None, "match": None,
        "identical_fraction": None, "oracle_rows": None, "row_count_match": None, "schema_match": None,
        "attempts_total": None, "judge_invocations": None, "convergence": {}, "class_counts": {},
        "tokens": _zero_tokens(), "cost": _cost_json(_new_cost()), "runtime_seconds": 0.0,
        "hpc_seconds": 0.0, "actual_elapsed_seconds": None, "attempts": [], "hpc_jobs": [],
        "agents": [], "by_model": [], "source_sql_path": None, "history": [],
    }


def _aggregate(concepts: Sequence[Mapping[str, Any]], rates: Optional[Mapping[str, Mapping[str, float]]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    agents: dict[str, dict[str, Any]] = {}
    models: dict[str, dict[str, Any]] = {}
    for concept in concepts:
        for entry in concept["agents"]:
            slot = agents.setdefault(entry["agent"], {
                "agent": entry["agent"], "tokens": _zero_tokens(), "seconds": 0.0,
                "messages": 0, "concepts": 0, "cost": _new_cost(), "models": set(),
            })
            slot["tokens"] = _add_tokens(slot["tokens"], entry["tokens"])
            slot["seconds"] += entry["seconds"]
            slot["messages"] += entry["messages"]
            slot["concepts"] += 1
            slot["models"] |= set(entry["models"])
            _add_cost(slot["cost"], entry["cost"])
        for entry in concept["by_model"]:
            slot = models.setdefault(entry["key"], {
                "key": entry["key"], "provider": entry["provider"], "model": entry["model"],
                "variant": entry["variant"], "rate_key": entry["rate_key"],
                "tokens": _zero_tokens(), "sessions": 0, "concepts": 0, "cost": _new_cost(),
            })
            slot["tokens"] = _add_tokens(slot["tokens"], entry["tokens"])
            slot["sessions"] += entry["session_count"]
            slot["concepts"] += 1
            _add_cost(slot["cost"], _price(entry["tokens"], entry["rate_key"], rates))

    agent_rows = [
        {**slot, "models": sorted(slot["models"]), "seconds": round(slot["seconds"], 3), "cost": _cost_json(slot["cost"])}
        for slot in sorted(agents.values(), key=lambda item: -item["tokens"]["total"])
    ]
    model_rows = [
        {**slot, "cost": _cost_json(slot["cost"])}
        for slot in sorted(models.values(), key=lambda item: -item["tokens"]["total"])
    ]
    return agent_rows, model_rows


def _kpis(concepts: Sequence[Mapping[str, Any]], denominator: Optional[int]) -> dict[str, Any]:
    ported = [item for item in concepts if item["status"] in (*PORTED_STATUSES, PORTED_NO_METRICS)]
    measured = [item for item in ported if item["has_metrics"]]
    attempts = [item["attempts_total"] for item in measured if item["attempts_total"] is not None]
    fractions = [item["identical_fraction"] for item in measured if item["identical_fraction"] is not None]
    total_tokens = sum(item["tokens"]["total"] for item in concepts)
    cost = _new_cost()
    for item in concepts:
        _add_cost(cost, {**item["cost"], "unpriced": set(item["cost"]["unpriced"])})
    return {
        "total_concepts": denominator if denominator is not None else len(concepts),
        "denominator_from_dag": denominator is not None,
        "ported": len(ported),
        "ported_with_metrics": len(measured),
        "ported_no_metrics": len(ported) - len(measured),
        "status_counts": {status: sum(item["status"] == status for item in concepts) for status in
                          (*TERMINAL_STATUSES, PORTED_NO_METRICS, "IN_PROGRESS", "NOT_STARTED")},
        "in_progress": sum(item["status"] == "IN_PROGRESS" for item in concepts),
        "total_tokens": total_tokens,
        "total_cost": _cost_json(cost),
        "total_runtime_seconds": round(sum(item["runtime_seconds"] for item in concepts), 3),
        "total_hpc_seconds": round(sum(item["hpc_seconds"] for item in concepts), 3),
        "mean_attempts": round(sum(attempts) / len(attempts), 2) if attempts else None,
        "mean_identical_fraction": round(sum(fractions) / len(fractions), 6) if fractions else None,
        "first_pass_rate": round(sum(value == 1 for value in attempts) / len(attempts), 4) if attempts else None,
    }


def build_report_data(
    *,
    artifact_root: Optional[str | Path] = None,
    rates_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Roll every metrics artifact, the DAG and the state dir into one payload."""
    root = _resolve_artifact_root(artifact_root)
    metrics_dir = root / METRICS_DIR
    rates_file = Path(rates_path) if rates_path else metrics_dir / RATES_NAME
    notes: list[str] = []

    rates, rates_note = _load_rates(rates_file)
    if rates_note:
        notes.append(rates_note)

    runs = _collect_runs(metrics_dir, notes)
    controller, dag = _dag_view(root, notes)

    concepts = [_concept_rollup(concept, values, rates) for concept, values in sorted(runs.items())]
    known = {item["concept"] for item in concepts}
    if dag is not None:
        for item in concepts:
            item["in_dag"] = item["concept"] in dag
            item["state_status"] = _state_status(controller, item["concept"], notes) if item["in_dag"] else None
            # A metrics artifact is write-once and finalized before the loop's
            # terminal response, so it records the status the *run* ended on.
            # Two things happen to a concept afterwards that the artifact
            # therefore cannot carry: a human override
            # (`BLOCKED_REPRESENTATION -> COMPLETED_WITH_DIVERGENCE`), and a
            # `retry` or `reopen` that puts it back in flight. Reporting the
            # artifact's status as the concept's would keep calling an
            # overridden concept blocked forever, and would show a superseded
            # verdict for one that is currently running.
            #
            # state.json is authoritative for what a concept *is*; the artifact
            # stays authoritative for what its run cost and measured, and is
            # kept under `metrics_status` so neither claim is lost.
            state_status = item["state_status"]
            if item["has_metrics"] and state_status and state_status != item["status"]:
                item["metrics_status"] = item["status"]
                if state_status in TERMINAL_STATUSES:
                    item["status"] = state_status
                    notes.append(
                        f"{item['concept']}: state.json is {state_status} but its "
                        f"last metrics artifact finalized on "
                        f"{item['metrics_status']}. Reporting the state; the "
                        "artifact is write-once and still describes that run "
                        "correctly."
                    )
                else:
                    item["status"] = "IN_PROGRESS"
                    notes.append(
                        f"{item['concept']}: back in flight ({state_status}); "
                        f"its last metrics artifact finalized on "
                        f"{item['metrics_status']}, which that run is still "
                        "reported under. The concept has no current verdict."
                    )
        unfinalized = []
        for concept in sorted(dag - known):
            status = _state_status(controller, concept, notes)
            if status in TERMINAL_STATUSES:
                unfinalized.append(f"{concept} ({status})")
            concepts.append(_placeholder(concept, status))
        if unfinalized:
            # A terminal state with no artifact is a missing finalize, not a missing port,
            # so a ported one counts toward progress -- but it stays a distinct status and
            # is named here, because no artifact backs its fidelity or cost figures.
            notes.append(
                "Terminal state.json but no metrics artifact (counted as ported where the state says so; "
                "contributes no tokens, cost or runtime): " + ", ".join(unfinalized)
            )
        outside = sorted(known - dag)
        if outside:
            notes.append("Metrics present for concept(s) not in the DAG: " + ", ".join(outside))
    concepts.sort(key=lambda item: item["concept"])

    by_agent, by_model = _aggregate(concepts, rates)
    kpis = _kpis(concepts, len(dag) if dag is not None else None)
    unpriced = sorted({key for row in by_model for key in row["cost"]["unpriced"]})
    if unpriced:
        notes.append("No rates entry for model(s): " + ", ".join(unpriced) + " (their cost shows as -, totals as $X.XX+)")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact_root": str(root),
        "metrics_dir": str(metrics_dir),
        "rates_path": str(rates_file),
        "has_costs": rates is not None,
        "schema_version": METRICS_SCHEMA_VERSION,
        "notes": notes,
        "unpriced_models": unpriced,
        "kpis": kpis,
        "concepts": concepts,
        "by_agent": by_agent,
        "by_model": by_model,
    }


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _thousands(value: Optional[float]) -> str:
    return "&mdash;" if value is None else f"{int(value):,}"


def _fraction(value: Optional[float]) -> str:
    return "&mdash;" if value is None else f"{value:.6f}"


def _percent(value: Optional[float]) -> str:
    return "&mdash;" if value is None else f"{value * 100:.1f}%"


def _duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "&mdash;"
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def _cost_cell(cost: Optional[Mapping[str, Any]], has_costs: bool) -> str:
    if not has_costs or cost is None:
        return "&mdash;"
    if cost["priced"] == 0:
        if not cost["unpriced"]:
            return "&mdash;"
        return f'<span class="muted" title="no rates for: {_e(", ".join(cost["unpriced"]))}">&mdash;</span>'
    text = f"${cost['value']:,.2f}"
    if cost["unpriced"]:
        return f'<span title="excludes unpriced model(s): {_e(", ".join(cost["unpriced"]))}">{text}+</span>'
    return text


def _cost_sort(cost: Optional[Mapping[str, Any]]) -> float:
    return -1.0 if cost is None else float(cost["value"])


def _bar(share: float) -> str:
    width = max(0.0, min(100.0, share * 100.0))
    return f'<div class="bar"><span style="width:{width:.1f}%"></span></div><small>{width:.1f}%</small>'


def _kv(pairs: Sequence[tuple[str, str]]) -> str:
    items = "".join(f"<div><dt>{_e(label)}</dt><dd>{value}</dd></div>" for label, value in pairs)
    return f"<dl class='kv'>{items}</dl>"


def _mini_table(headers: Sequence[str], rows: Sequence[Sequence[str]], empty: str) -> str:
    if not rows:
        return f"<p class='muted'>{_e(empty)}</p>"
    head = "".join(f"<th>{_e(name)}</th>" for name in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table class='mini'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _detail(item: Mapping[str, Any], has_costs: bool, columns: int) -> str:
    if not item["has_metrics"]:
        label = {
            "IN_PROGRESS": "Concept is mid-flight",
            PORTED_NO_METRICS: "Concept was ported before metrics tracking existed",
        }.get(item["status"], "Concept has not been started")
        state = f" (state: {_e(item['state_status'])})" if item["state_status"] else ""
        return (f"<tr class='detail'><td colspan='{columns}'><div class='detail-body'>"
                f"<p class='muted'>{label}{state}. No metrics artifact yet.</p></div></td></tr>")

    attempts = _mini_table(
        ["attempt", "demo", "full verdict", "tier", "hpc job", "judge"],
        [[
            _e(row["attempt"]), _e(row["demo_verdict"] or "-"), _e(row["full_verdict"] or "-"),
            _e(row["full_tier"] or "-"), "yes" if row["hpc_job_submitted"] else "no",
            "yes" if row["judge_invoked"] else "no",
        ] for row in item["attempts"]],
        "No per-attempt records.",
    )
    classes = _mini_table(
        ["class", "rows"],
        [[_e(name.replace("_", " ")), _thousands(count)] for name, count in item["class_counts"].items()],
        "No comparator class counts (final_comparator absent).",
    )
    agent_headers = ["agent", "tokens", "messages", "time"] + (["est. cost"] if has_costs else []) + ["model(s)"]
    agent_rows = []
    for row in item["agents"]:
        cells = [_e(row["agent"]), _thousands(row["tokens"]["total"]), _thousands(row["messages"]), _duration(row["seconds"])]
        if has_costs:
            cells.append(_cost_cell(row["cost"], has_costs))
        cells.append(_e(", ".join(row["models"]) or "-"))
        agent_rows.append(cells)
    agents = _mini_table(agent_headers, agent_rows, "No per-agent records.")
    jobs = _mini_table(
        ["run", "attempt", "runtime", "source", "accounting"],
        [[
            _e(row["run"]), _e(row["attempt"]), _duration(row["runtime_seconds"]),
            _e(row["runtime_source"] or "-"), "yes" if row["accounting_present"] else "no",
        ] for row in item["hpc_jobs"]],
        "No HPC jobs recorded.",
    )
    models = _mini_table(
        ["provider/model/variant", "sessions", "tokens"],
        [[_e(row["key"]), _thousands(row["session_count"]), _thousands(row["tokens"]["total"])]
         for row in item["by_model"]],
        "No model records.",
    )

    history = ""
    if item["runs"] > 1:
        history_headers = ["run", "status", "verdict", "tokens"] + (["est. cost"] if has_costs else []) + ["runtime"]
        history_rows = []
        for row in item["history"]:
            cells = [_e(row["run"]), _e(row["status"]), _e(row["verdict"] or "-"), _thousands(row["tokens"])]
            if has_costs:
                cells.append(_cost_cell(row["cost"], has_costs))
            cells.append(_duration(row["runtime_seconds"]))
            history_rows.append(cells)
        history = f"<section><h4>Run history ({item['runs']} runs)</h4>{_mini_table(history_headers, history_rows, '-')}</section>"

    tokens = item["tokens"]
    convergence = item["convergence"]
    facts = _kv([
        ("source SQL", _e(item["source_sql_path"] or "-")),
        ("runs", _e(", ".join(f"run_{number:04d}" for number in item["run_numbers"]) or "-")),
        ("row count match", _e(item["row_count_match"])),
        ("schema match", _e(item["schema_match"])),
        ("comparator match", _e(item["match"])),
        ("divergence decided by", _e(convergence.get("divergence_decided_by") or "-")),
        ("human override", _e(convergence.get("human_manual_override"))),
        ("semantic rework cycles", _e(convergence.get("semantic_rework_cycles"))),
        ("engineering counter", _e(convergence.get("engineering_counter"))),
        ("hpc counter", _e(convergence.get("hpc_counter"))),
        ("submitted jobs", _e(convergence.get("submitted_jobs"))),
        ("full validation rounds", _e(convergence.get("full_validation_rounds"))),
        ("input / output tokens", f"{_thousands(tokens['input'])} / {_thousands(tokens['output'])}"),
        ("reasoning / cache read / cache write",
         f"{_thousands(tokens['reasoning'])} / {_thousands(tokens['cache_read'])} / {_thousands(tokens['cache_write'])}"),
        ("hpc accounted", _duration(item["hpc_seconds"])),
        ("wall-clock elapsed (latest run)", _duration(item["actual_elapsed_seconds"])),
    ])
    return (
        f"<tr class='detail'><td colspan='{columns}'><div class='detail-body'>"
        f"<section><h4>Summary</h4>{facts}</section>"
        f"<section><h4>Per-attempt verdicts</h4>{attempts}</section>"
        f"<section><h4>Divergence classes</h4>{classes}</section>"
        f"<section><h4>Per-agent usage</h4>{agents}</section>"
        f"<section><h4>HPC jobs</h4>{jobs}</section>"
        f"<section><h4>Models used</h4>{models}</section>"
        f"{history}"
        "</div></td></tr>"
    )


def _status_cell(item: Mapping[str, Any]) -> str:
    label = STATUS_LABELS.get(item["status"], item["status"])
    css = STATUS_CLASSES.get(item["status"], "muted")
    title = f' title="state.json status: {_e(item["state_status"])}"' if item["state_status"] and not item["has_metrics"] else ""
    badge = f"<span class='pill {css}'{title}>{_e(label)}</span>"
    if item["runs"] > 1:
        badge += f" <span class='pill runs'>{item['runs']} runs</span>"
    return badge


def _concept_table(data: Mapping[str, Any]) -> str:
    has_costs = bool(data["has_costs"])
    headers = [
        ("concept", "concept", ""), ("status", "status", ""), ("verdict", "verdict / tier", ""),
        ("identical", "identical fraction", "num"), ("oracle", "oracle rows", "num"),
        ("attempts", "attempts", "num"), ("judge", "judge calls", "num"),
        ("tokens", "tokens", "num"),
    ]
    if has_costs:
        headers.append(("cost", "est. cost", "num"))
    headers.append(("runtime", "runtime", "num"))
    head = "".join(
        f"<th data-col='{key}' class='{css}' title='click to sort'>{_e(label)}</th>" for key, label, css in headers
    )
    rows = []
    for item in data["concepts"]:
        verdict = " / ".join(part for part in (item["verdict"], item["tier"]) if part) or "&mdash;"
        cells = [
            f"<td data-col='concept' data-sort='{_e(item['concept'])}'><span class='toggle'>&#9656;</span> {_e(item['concept'])}</td>",
            f"<td data-col='status' data-sort='{_e(item['status'])}'>{_status_cell(item)}</td>",
            f"<td data-col='verdict' data-sort='{_e(item['verdict'] or '')}'>{verdict}</td>",
            f"<td data-col='identical' class='num' data-sort='{item['identical_fraction'] if item['identical_fraction'] is not None else -1}'>{_fraction(item['identical_fraction'])}</td>",
            f"<td data-col='oracle' class='num' data-sort='{item['oracle_rows'] if item['oracle_rows'] is not None else -1}'>{_thousands(item['oracle_rows'])}</td>",
            f"<td data-col='attempts' class='num' data-sort='{item['attempts_total'] if item['attempts_total'] is not None else -1}'>{_thousands(item['attempts_total'])}</td>",
            f"<td data-col='judge' class='num' data-sort='{item['judge_invocations'] if item['judge_invocations'] is not None else -1}'>{_thousands(item['judge_invocations'])}</td>",
            # A concept with no artifact has no measurement -- render it unknown, not zero.
            f"<td data-col='tokens' class='num' data-sort='{item['tokens']['total']}'>"
            f"{_thousands(item['tokens']['total']) if item['has_metrics'] else '&mdash;'}</td>",
        ]
        if has_costs:
            cells.append(
                f"<td data-col='cost' class='num' data-sort='{_cost_sort(item['cost'])}'>{_cost_cell(item['cost'], True)}</td>"
            )
        cells.append(
            f"<td data-col='runtime' class='num' data-sort='{item['runtime_seconds']}'>"
            f"{_duration(item['runtime_seconds']) if item['has_metrics'] else '&mdash;'}</td>"
        )
        rows.append("<tr class='row'>" + "".join(cells) + "</tr>" + _detail(item, has_costs, len(headers)))
    return (
        "<table id='concepts' class='grid'><thead><tr>" + head + "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _share_table(
    title: str, label: str, rows: Sequence[Mapping[str, Any]], has_costs: bool, extra: Sequence[tuple[str, Any]],
) -> str:
    total_tokens = sum(row["tokens"]["total"] for row in rows) or 1
    total_cost = sum(row["cost"]["value"] for row in rows) or 1.0
    headers = [label, "tokens", "token share"]
    if has_costs:
        headers += ["est. cost", "cost share"]
    headers += [name for name, _ in extra] + ["time"]
    body = []
    for row in rows:
        cells = [
            _e(row.get("agent") or row.get("key")),
            _thousands(row["tokens"]["total"]),
            _bar(row["tokens"]["total"] / total_tokens),
        ]
        if has_costs:
            cells += [_cost_cell(row["cost"], True), _bar(row["cost"]["value"] / total_cost)]
        cells += [_e(row.get(key)) for _, key in extra]
        cells.append(_duration(row["seconds"]) if "seconds" in row else "&mdash;")
        body.append(cells)
    return f"<h2>{_e(title)}</h2>" + _mini_table(headers, body, "No data.")


def _kpi_tiles(data: Mapping[str, Any]) -> str:
    kpis = data["kpis"]
    total, ported = kpis["total_concepts"], kpis["ported"]
    share = (ported / total) if total else 0.0
    tiles = [
        ("Ported", f"{ported}/{total}", f"{share * 100:.0f}% of {'DAG concepts' if kpis['denominator_from_dag'] else 'concepts with metrics'}"
                                        + (f", {kpis['ported_no_metrics']} without metrics" if kpis["ported_no_metrics"] else "")),
        ("Completed", str(kpis["status_counts"].get("COMPLETED", 0)), "clean comparator match"),
        ("Completed w/ divergence", str(kpis["status_counts"].get("COMPLETED_WITH_DIVERGENCE", 0)), "judge-accepted divergence"),
        ("Ported (no metrics)", str(kpis["ported_no_metrics"]), "predates the tracker; no cost data"),
        ("Failed", str(kpis["status_counts"].get("FAILED", 0)), "terminal failure"),
        ("Blocked (representation)", str(kpis["status_counts"].get("BLOCKED_REPRESENTATION", 0)), "not representable"),
        ("In progress", str(kpis["in_progress"]), "non-terminal state.json"),
        ("Total tokens", f"{kpis['total_tokens']:,}", "all runs, all agents"),
    ]
    if data["has_costs"]:
        tiles.append(("Total est. cost", _cost_cell(kpis["total_cost"], True), "estimate from rates.json"))
    tiles += [
        ("Total runtime", _duration(kpis["total_runtime_seconds"]), "agent busy time + HPC"),
        ("HPC seconds", _duration(kpis["total_hpc_seconds"]), "Slurm-accounted"),
        ("Mean attempts", "&mdash;" if kpis["mean_attempts"] is None else f"{kpis['mean_attempts']:.2f}", "per ported concept"),
        ("Mean identical fraction", _fraction(kpis["mean_identical_fraction"]), "per ported concept"),
        ("First-pass rate", _percent(kpis["first_pass_rate"]), "ported in a single attempt"),
    ]
    return "<div class='tiles'>" + "".join(
        f"<div class='tile'><div class='tile-label'>{_e(label)}</div><div class='tile-value'>{value}</div>"
        f"<div class='tile-note'>{_e(note)}</div></div>" for label, value, note in tiles
    ) + "</div>"


def _banner(data: Mapping[str, Any]) -> str:
    notes = data["notes"]
    if not notes:
        return ""
    items = "".join(f"<li>{_e(note)}</li>" for note in notes)
    return f"<div class='banner'><strong>Inputs skipped or degraded</strong><ul>{items}</ul></div>"


def render_report(data: Mapping[str, Any]) -> str:
    """Render the whole self-contained page.  No external requests."""
    payload = json.dumps(data, indent=None, sort_keys=True, ensure_ascii=False, default=str)
    # A literal "</script>" or "<!--" inside any string would end the tag early.
    payload = payload.replace("<", "\\u003c")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MIMIC-on-FHIR conversion metrics</title>
<style>
:root {{ color-scheme: light; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 24px; font: 14px/1.5 -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       color: #1c1f23; background: #f6f7f9; }}
h1 {{ font-size: 22px; margin: 0 0 4px; }}
h2 {{ font-size: 16px; margin: 32px 0 10px; }}
h4 {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #5b6570; margin: 0 0 6px; }}
.sub {{ color: #5b6570; margin: 0 0 20px; }}
.banner {{ background: #fff7e6; border: 1px solid #f0d9a8; border-radius: 6px; padding: 10px 14px; margin: 0 0 20px; }}
.banner ul {{ margin: 6px 0 0; padding-left: 20px; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }}
.tile {{ background: #fff; border: 1px solid #e0e4e9; border-radius: 6px; padding: 10px 12px; }}
.tile-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .04em; color: #5b6570; }}
.tile-value {{ font-size: 21px; font-weight: 600; margin: 2px 0; }}
.tile-note {{ font-size: 11px; color: #7b848e; }}
table {{ border-collapse: collapse; width: 100%; background: #fff; }}
.grid {{ border: 1px solid #e0e4e9; border-radius: 6px; overflow: hidden; }}
.grid th, .grid td {{ padding: 7px 10px; border-bottom: 1px solid #eceff2; text-align: left; vertical-align: top; }}
.grid th {{ background: #f0f2f5; font-size: 12px; cursor: pointer; user-select: none; white-space: nowrap; }}
.grid th.asc::after {{ content: " \\25B2"; }}
.grid th.desc::after {{ content: " \\25BC"; }}
.grid tr.row {{ cursor: pointer; }}
.grid tr.row:hover {{ background: #f8fafc; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.num {{ text-align: right; }}
.toggle {{ display: inline-block; width: 10px; color: #98a1ab; transition: transform .1s; }}
tr.expanded .toggle {{ transform: rotate(90deg); }}
tr.detail {{ display: none; }}
tr.detail.open {{ display: table-row; }}
.detail-body {{ background: #fbfcfd; padding: 12px 14px 4px 24px; display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }}
.detail-body section {{ min-width: 0; overflow-x: auto; }}
.mini {{ font-size: 12px; border: 1px solid #e5e9ee; }}
.mini th, .mini td {{ padding: 4px 8px; border-bottom: 1px solid #eef1f4; text-align: left; white-space: nowrap; }}
.mini th {{ background: #f4f6f8; font-weight: 600; }}
.kv {{ margin: 0; font-size: 12px; }}
.kv div {{ display: flex; gap: 8px; border-bottom: 1px solid #eef1f4; padding: 2px 0; }}
.kv dt {{ color: #5b6570; flex: 0 0 45%; }}
.kv dd {{ margin: 0; word-break: break-word; }}
.pill {{ display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 11px; white-space: nowrap; }}
.pill.ok {{ background: #e3f4e6; color: #1d6b2c; }}
.pill.warn {{ background: #fdf1da; color: #8a5a06; }}
.pill.bad {{ background: #fce6e6; color: #9c2020; }}
.pill.info {{ background: #e4eefc; color: #1d4e89; }}
.pill.pale {{ background: #eef4ef; color: #4c6b55; border: 1px dashed #9db8a6; }}
.pill.muted {{ background: #eef0f3; color: #5b6570; }}
.pill.runs {{ background: #eae6fb; color: #4b3a94; }}
.muted {{ color: #7b848e; }}
.bar {{ display: inline-block; width: 90px; height: 8px; background: #eceff2; border-radius: 4px;
        overflow: hidden; vertical-align: middle; margin-right: 6px; }}
.bar span {{ display: block; height: 100%; background: #6b8fd6; }}
small {{ color: #5b6570; font-variant-numeric: tabular-nums; }}
footer {{ margin-top: 32px; color: #7b848e; font-size: 12px; }}
</style>
</head>
<body>
<h1>MIMIC-on-FHIR conversion metrics</h1>
<p class="sub">Generated {_e(data["generated_at"])} &middot; artifact root <code>{_e(data["artifact_root"])}</code>
{"&middot; costs are <strong>estimates</strong> from <code>" + _e(Path(str(data["rates_path"])).name) + "</code>" if data["has_costs"] else "&middot; cost columns omitted (no usable rates table)"}</p>
{_banner(data)}
{_kpi_tiles(data)}
<h2>Concepts</h2>
<p class="sub">Headline fields come from the highest-numbered run; tokens, cost and runtime are summed across every run.
Click a header to sort, click a row to expand.</p>
{_concept_table(data)}
{_share_table("By agent", "agent", data["by_agent"], data["has_costs"], [("concepts", "concepts")])}
{_share_table("By model", "provider/model/variant", data["by_model"], data["has_costs"], [("concepts", "concepts")])}
<footer>All costs are estimates: rate &times; (input + cache read + cache write) and rate &times; (output + reasoning),
per 1M tokens; the model variant is not priced separately. Rolled-up data is embedded below as JSON.</footer>
<script type="application/json" id="data">{payload}</script>
<script>
(function () {{
  var table = document.getElementById("concepts");
  if (!table) return;
  var body = table.tBodies[0];
  var dir = {{}};
  function pairs() {{
    var out = [], rows = body.rows;
    for (var i = 0; i + 1 < rows.length; i += 2) out.push([rows[i], rows[i + 1]]);
    return out;
  }}
  function key(row, col) {{
    var cell = row.querySelector('[data-col="' + col + '"]');
    var raw = cell ? (cell.getAttribute("data-sort") || "") : "";
    return /^-?\\d+(\\.\\d+)?([eE][-+]?\\d+)?$/.test(raw.trim()) ? parseFloat(raw) : raw.toLowerCase();
  }}
  function sort(col) {{
    var asc = dir[col] = !dir[col];
    var items = pairs();
    items.sort(function (a, b) {{
      var x = key(a[0], col), y = key(b[0], col);
      if (x < y) return asc ? -1 : 1;
      if (x > y) return asc ? 1 : -1;
      return 0;
    }});
    items.forEach(function (pair) {{ body.appendChild(pair[0]); body.appendChild(pair[1]); }});
    Array.prototype.forEach.call(table.querySelectorAll("th[data-col]"), function (th) {{
      var on = th.getAttribute("data-col") === col;
      th.className = th.className.replace(/\\s*(asc|desc)/g, "") + (on ? (asc ? " asc" : " desc") : "");
    }});
  }}
  Array.prototype.forEach.call(table.querySelectorAll("th[data-col]"), function (th) {{
    th.addEventListener("click", function () {{ sort(th.getAttribute("data-col")); }});
  }});
  body.addEventListener("click", function (event) {{
    var row = event.target.closest ? event.target.closest("tr.row") : null;
    if (!row) return;
    var detail = row.nextElementSibling;
    if (detail && detail.className.indexOf("detail") >= 0) detail.classList.toggle("open");
    row.classList.toggle("expanded");
  }});
}})();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: str) -> None:
    """Overwrite *path* atomically.  Unlike the run artifacts this is not write-once."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".report-", suffix=".tmp", dir=path.parent)
    except OSError as exc:
        raise ReportError(f"Cannot write metrics report to {path}: {exc}") from exc
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        temporary.unlink(missing_ok=True)
        raise ReportError(f"Cannot write metrics report to {path}: {exc}") from exc


def generate_metrics_report(
    *,
    out: Optional[str | Path] = None,
    rates_path: Optional[str | Path] = None,
    artifact_root: Optional[str | Path] = None,
) -> Path:
    """Roll up every metrics artifact and write the self-contained HTML report."""
    root = _resolve_artifact_root(artifact_root)
    output = Path(out) if out else root / METRICS_DIR / REPORT_NAME
    data = build_report_data(artifact_root=root, rates_path=rates_path)
    _atomic_write(output, render_report(data))
    return output


__all__ = ["ReportError", "build_report_data", "generate_metrics_report", "render_report"]
