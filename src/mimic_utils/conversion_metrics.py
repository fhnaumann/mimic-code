"""Deterministic write-once metrics for a terminal concept conversion.

Only the current OpenCode 1.18.9, ConversionState, and comparator formats are
supported.  Unknown required fields fail rather than being guessed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from mimic_utils.conversion_state import ConversionController, StateError

METRICS_SCHEMA_VERSION = "conversion-metrics.v2"
TRACKER_SCHEMA_VERSION = "1"
TERMINAL_STATUSES = frozenset({"COMPLETED", "COMPLETED_WITH_DIVERGENCE", "FAILED", "BLOCKED_REPRESENTATION"})
SEMANTIC_TERMINAL_STATUSES = frozenset({"COMPLETED_WITH_DIVERGENCE", "BLOCKED_REPRESENTATION"})
ATTEMPT_RE = re.compile(r"^attempt_(\d{4})$")
POLL_RE = re.compile(r"(?:^|\s)mimic_utils\s+hpc-poll\s+([A-Za-z0-9_-]+)(?:\s|$)")
SESSION_COLUMNS = (
    "id", "project_id", "parent_id", "directory", "version", "agent", "model",
    "time_created", "time_updated", "tokens_input", "tokens_output",
    "tokens_reasoning", "tokens_cache_read", "tokens_cache_write",
)
TOKEN_NAMES = ("input", "output", "reasoning", "cache_read", "cache_write")
COMPARISON_CLASSES = (
    "only_oracle", "only_candidate", "differing_null_only", "differing_conflict",
    "differing", "identical", "identical_representable",
)


class MetricsError(StateError):
    """The requested metrics artifact cannot be safely finalized."""


def _json_file(path: Path) -> Optional[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _epoch_ms(value: Any) -> Optional[float]:
    try:
        return None if value is None else float(value) / 1000.0
    except (TypeError, ValueError):
        return None


def _iso_epoch(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.timestamp()


def _round(value: Optional[float]) -> Optional[float]:
    return None if value is None else round(value, 6)


def _zero_tokens() -> dict[str, int]:
    return {**{name: 0 for name in TOKEN_NAMES}, "total": 0}


def _tokens(row: Mapping[str, Any]) -> dict[str, int]:
    result = {
        "input": int(row["tokens_input"] or 0),
        "output": int(row["tokens_output"] or 0),
        "reasoning": int(row["tokens_reasoning"] or 0),
        "cache_read": int(row["tokens_cache_read"] or 0),
        "cache_write": int(row["tokens_cache_write"] or 0),
    }
    result["total"] = sum(result.values())
    return result


def _add_tokens(left: Mapping[str, int], right: Mapping[str, int]) -> dict[str, int]:
    result = {name: int(left.get(name, 0)) + int(right.get(name, 0)) for name in (*TOKEN_NAMES, "total")}
    result["total"] = sum(result[name] for name in TOKEN_NAMES)
    return result


def _model_parts(row: Mapping[str, Any]) -> tuple[str, str, Optional[str]]:
    try:
        model = json.loads(row["model"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise MetricsError(f"Invalid session.model JSON for session {row['id']!r}") from exc
    if not isinstance(model, dict) or "id" not in model or "providerID" not in model:
        raise MetricsError(f"session.model lacks current id/providerID fields for session {row['id']!r}")
    model_id, provider = _text(model["id"]), _text(model["providerID"])
    if model_id is None or provider is None:
        raise MetricsError(f"session.model has empty id/providerID for session {row['id']!r}")
    return provider, model_id, _text(model.get("variant"))


def _model_key(provider: str, model: str, variant: Optional[str]) -> str:
    return "/".join((provider, model, variant or "unknown"))


def _union(intervals: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted(intervals)
    if not ordered:
        return []
    merged: list[list[float]] = [[ordered[0][0], ordered[0][1]]]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _duration(intervals: Sequence[tuple[float, float]]) -> float:
    return sum(end - start for start, end in _union(intervals))


def _overlap(left: Sequence[tuple[float, float]], right: Sequence[tuple[float, float]]) -> float:
    a, b = _union(left), _union(right)
    i = j = 0
    total = 0.0
    while i < len(a) and j < len(b):
        start, end = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if end > start:
            total += end - start
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def _marks(values: Sequence[Any]) -> str:
    return ",".join("?" for _ in values)


def _check_schema(db: sqlite3.Connection) -> set[str]:
    required = {
        "session": set(SESSION_COLUMNS),
        "message": {"id", "session_id", "data"},
        "part": {"id", "message_id", "session_id", "data"},
        "project": {"id", "worktree"},
    }
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    for table, columns in required.items():
        if table not in tables:
            raise MetricsError(f"OpenCode database is missing table {table!r}")
        actual = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        missing = sorted(columns - actual)
        if missing:
            raise MetricsError(f"OpenCode table {table!r} is missing current column(s): {', '.join(missing)}")
    return tables


def _sessions(db: sqlite3.Connection, column: str, ids: Sequence[str]) -> list[dict[str, Any]]:
    if column not in {"id", "parent_id"}:
        raise MetricsError(f"Invalid internal session selector {column!r}")
    if not ids:
        return []
    query = f"SELECT {', '.join(SESSION_COLUMNS)} FROM session WHERE {column} IN ({_marks(ids)})"
    return [dict(row) for row in db.execute(query, list(ids)).fetchall()]


def _same_directory(value: str, expected: Path) -> bool:
    try:
        return Path(value).expanduser().resolve() == expected
    except OSError:
        return False


def _scope_sessions(db: sqlite3.Connection, supplied: Sequence[str], root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    roots = sorted({value.strip() for value in supplied if value.strip()})
    if not roots:
        raise MetricsError("At least one --session-id is required")
    root_rows = _sessions(db, "id", roots)
    if len(root_rows) != len(roots):
        missing = sorted(set(roots) - {row["id"] for row in root_rows})
        raise MetricsError("OpenCode root session(s) not found: " + ", ".join(missing))
    if any(row["parent_id"] is not None for row in root_rows):
        bad = sorted(row["id"] for row in root_rows if row["parent_id"] is not None)
        raise MetricsError("Supplied session(s) must be root sessions (parent_id NULL): " + ", ".join(bad))
    project_ids = sorted({row["project_id"] for row in root_rows})
    projects = {
        row[0]: row[1]
        for row in db.execute(
            f"SELECT id, worktree FROM project WHERE id IN ({_marks(project_ids)})", project_ids
        ).fetchall()
    }
    for row in root_rows:
        if row["project_id"] not in projects:
            raise MetricsError(f"Project for root session {row['id']!r} was not found")
        if not _same_directory(row["directory"], root) or not _same_directory(projects[row["project_id"]], root):
            raise MetricsError(f"Root session {row['id']!r} is not in project directory {root}")

    scoped = {row["id"]: row for row in root_rows}
    owners = {row["id"]: row["id"] for row in root_rows}
    frontier = roots
    while frontier:
        children = _sessions(db, "parent_id", frontier)
        next_frontier = []
        for row in children:
            session_id, owner = row["id"], owners[row["parent_id"]]
            if session_id in scoped:
                previous = owners[session_id]
                if previous != owner:
                    raise MetricsError(
                        f"Session descendant {session_id!r} would be counted under roots {previous!r} and {owner!r}"
                    )
                raise MetricsError(f"Cycle or duplicate descendant at {session_id!r}")
            scoped[session_id], owners[session_id] = row, owner
            next_frontier.append(session_id)
        frontier = sorted(set(next_frontier))
    return [scoped[key] for key in sorted(scoped)], roots


def _scoped_data(db: sqlite3.Connection, session_ids: Sequence[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    marks, values = _marks(session_ids), list(session_ids)
    messages = [dict(row) for row in db.execute(
        f"SELECT id, session_id, data FROM message WHERE session_id IN ({marks})", values
    ).fetchall()]
    parts = [dict(row) for row in db.execute(
        f"SELECT id, message_id, session_id, data FROM part WHERE session_id IN ({marks})", values
    ).fetchall()]
    return messages, parts


def _token_metrics(sessions: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    total, by_agent, by_model = _zero_tokens(), {}, {}
    models: set[tuple[str, str, Optional[str], str]] = set()
    versions: set[str] = set()
    for session in sessions:
        usage = _tokens(session)
        total = _add_tokens(total, usage)
        agent = _text(session["agent"]) or "unknown"
        entry = by_agent.setdefault(agent, {"session_count": 0, "tokens": _zero_tokens()})
        entry["session_count"], entry["tokens"] = entry["session_count"] + 1, _add_tokens(entry["tokens"], usage)
        provider, model, variant = _model_parts(session)
        key = _model_key(provider, model, variant)
        entry = by_model.setdefault(key, {
            "provider": provider, "model": model, "variant": variant,
            "session_count": 0, "tokens": _zero_tokens(),
        })
        entry["session_count"], entry["tokens"] = entry["session_count"] + 1, _add_tokens(entry["tokens"], usage)
        models.add((provider, model, variant, agent))
        versions.add(str(session["version"]))
    model_list = [
        {"provider": p, "model": m, "variant": v, "agent": a}
        for p, m, v, a in sorted(models, key=lambda x: tuple(value or "" for value in (x[3], *x[:3])))
    ]
    return {**total, "by_agent": by_agent, "by_model": by_model}, model_list, sorted(versions)


def _message_metrics(messages: Sequence[Mapping[str, Any]], agents: Mapping[str, str]) -> tuple[list[tuple[float, float]], dict[str, list[tuple[float, float]]], dict[str, int]]:
    intervals, by_agent = [], defaultdict(list)
    counts = {"assistant_messages": 0, "completed_assistant_messages": 0, "incomplete_assistant_messages": 0, "invalid_assistant_intervals": 0}
    for message in messages:
        data = json.loads(message["data"])
        if data.get("role") != "assistant":
            continue
        counts["assistant_messages"] += 1
        time_data = data.get("time")
        start = _epoch_ms(time_data.get("created")) if isinstance(time_data, dict) else None
        end = _epoch_ms(time_data.get("completed")) if isinstance(time_data, dict) else None
        if start is None or end is None:
            counts["incomplete_assistant_messages"] += 1
        elif end < start:
            counts["invalid_assistant_intervals"] += 1
        else:
            interval = (start, end)
            intervals.append(interval)
            by_agent[agents[message["session_id"]]].append(interval)
            counts["completed_assistant_messages"] += 1
    return intervals, dict(by_agent), counts


def _attempt_dirs(controller: ConversionController, concept: str) -> list[tuple[int, Path]]:
    source = controller.dag_raw["nodes"][concept]["path"].replace("\\", "/")
    category = source.split("/")[0] if "/" in source else "_root"
    base = controller.attempt_base / category / concept.replace("/", "_").replace("\\", "_").replace("..", "")
    if not base.is_dir():
        return []
    return sorted((int(match.group(1)), path) for path in base.iterdir() if path.is_dir() and (match := ATTEMPT_RE.match(path.name)))


def _comparison_summary(raw: Optional[Mapping[str, Any]]) -> Optional[dict[str, Any]]:
    if raw is None:
        return None
    if raw.get("format_version") != "2.0":
        raise MetricsError("comparison.full.json must use current format_version 2.0")
    required = {"verdict", "match", "row_count", "schema"}
    missing = sorted(required - set(raw))
    if missing:
        raise MetricsError("comparison.full.json is missing current field(s): " + ", ".join(missing))
    diff = raw.get("diff") if isinstance(raw.get("diff"), dict) else {}
    divergence = raw.get("divergence") if isinstance(raw.get("divergence"), dict) else {}
    fidelity = {key: divergence[key] for key in ("identical_fraction", "identical_rows", "oracle_rows", "representable_fraction") if key in divergence}
    if "representable_identical_rows" in divergence:
        fidelity["representable_identical_rows"] = divergence["representable_identical_rows"]
    elif "identical_representable_rows" in divergence:
        fidelity["representable_identical_rows"] = divergence["identical_representable_rows"]
    elif "identical_representable" in diff:
        fidelity["representable_identical_rows"] = diff["identical_representable"]
    row_count, schema = raw["row_count"], raw["schema"]
    fidelity["row_count"] = {key: row_count[key] for key in ("candidate", "oracle", "delta", "match", "gated") if key in row_count}
    fidelity["schema_match"] = schema["match"]
    return {
        "artifact_present": True,
        "verdict": raw["verdict"],
        "match": raw["match"],
        "classification": divergence.get("classification") or diff.get("classification"),
        "tier": divergence.get("tier"),
        "class_counts": {
            key: diff[key]
            for key in COMPARISON_CLASSES
            if isinstance(diff.get(key), (int, float)) and not isinstance(diff.get(key), bool)
        },
        "fidelity": fidelity,
    }


def _job_runtime(
    accounting: Optional[Mapping[str, Any]],
    run_meta: Optional[Mapping[str, Any]],
) -> tuple[Optional[float], Optional[str]]:
    if accounting is not None:
        elapsed = accounting.get("elapsed_seconds")
        if isinstance(elapsed, (int, float)) and not isinstance(elapsed, bool) and elapsed >= 0:
            return float(elapsed), "slurm_sacct_elapsed"
    timings = run_meta.get("timings_seconds") if run_meta is not None else None
    if isinstance(timings, dict):
        values = [timings.get("execute"), timings.get("compare")]
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 for value in values):
            return float(sum(values)), "run_meta_execute_compare"
    return None, None


def _attempt_metrics(attempts: Sequence[tuple[int, Path]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Optional[dict[str, Any]]]:
    summaries, jobs, latest = [], [], None
    for number, directory in attempts:
        comparison_path = directory / "comparison.full.json"
        comparison = _comparison_summary(_json_file(comparison_path)) if comparison_path.is_file() else None
        latest = comparison or latest
        shape = _json_file(directory / "shape.demo.json")
        shape = {key: shape[key] for key in ("verdict", "executed", "candidate_row_count") if key in shape} if shape else None
        hpc_path, hpc = directory / "hpc_job.json", _json_file(directory / "hpc_job.json")
        accounting_path = directory / "hpc_accounting.json"
        accounting = _json_file(accounting_path)
        runtime_seconds, runtime_source = _job_runtime(
            accounting, _json_file(directory / "run_meta.full.json")
        )
        if hpc_path.is_file():
            jobs.append({
                "attempt": number,
                "job_id": str(hpc["job_id"]) if hpc and "job_id" in hpc else None,
                "full_result_present": comparison_path.is_file(),
                "accounting_present": accounting_path.is_file(),
                "runtime_seconds": runtime_seconds,
                "runtime_source": runtime_source,
            })
        summaries.append({
            "attempt": number,
            "artifacts": sorted(path.name for path in directory.iterdir()),
            "convergence": {"demo": shape, "full": comparison, "hpc_job_submitted": hpc_path.is_file(), "judge_invoked": (directory / "evidence" / "equivalence-judge.md").is_file()},
            "usage_attribution": "unavailable",
        })
    return summaries, jobs, latest


def _flag(command: str, name: str) -> Optional[str]:
    words = shlex.split(command)
    for index, word in enumerate(words):
        if word == name and index + 1 < len(words):
            return words[index + 1]
        if word.startswith(name + "="):
            return word[len(name) + 1:]
    return None


def _poll_intervals(parts: Sequence[Mapping[str, Any]], session_ids: set[str], concept: str, jobs: Sequence[Mapping[str, Any]]) -> tuple[dict[int, list[tuple[float, float]]], int]:
    by_job_id = {str(job["job_id"]): i for i, job in enumerate(jobs) if job["job_id"] is not None}
    by_attempt = {job["attempt"]: i for i, job in enumerate(jobs)}
    matched, unmatched = defaultdict(list), 0
    for part in parts:
        if part["session_id"] not in session_ids:
            continue
        data = json.loads(part["data"])
        if data.get("type") != "tool" or data.get("tool") != "bash":
            continue
        state, command = data["state"], data["state"]["input"]["command"]
        match = POLL_RE.search(command)
        if match is None or match.group(1) != concept:
            continue
        start, end = _epoch_ms(state["time"]["start"]), _epoch_ms(state["time"]["end"])
        if start is None or end is None or end < start:
            continue
        index = by_job_id.get(_flag(command, "--job-id"))
        attempt = _flag(command, "--attempt")
        if index is None and attempt is not None:
            index = by_attempt.get(int(attempt))
        if index is None and len(jobs) == 1:
            index = 0
        if index is None:
            unmatched += 1
        else:
            matched[index].append((start, end))
    return dict(matched), unmatched


def _config_hashes(root: Path) -> dict[str, str]:
    files = ("opencode.json", ".opencode/agents/concept-port-orchestrator.md", ".opencode/skills/concept-orchestrator-loop/SKILL.md", "mimic-iv/concepts_fhir/LOOP_CONTRACT.md")
    return {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest() for relative in files if (root / relative).is_file()}


def _semantic_metrics(status: str, counter: int) -> dict[str, Any]:
    subtract = int(status in SEMANTIC_TERMINAL_STATUSES)
    return {
        "semantic_counter": counter,
        "semantic_rework_cycles": max(0, counter - subtract),
        "semantic_terminal_transition_subtracted": subtract,
        "semantic_rework_method": "max(0, semantic_counter - terminal semantic transition)",
        "semantic_rework_source": "ConversionState.semantic_counter plus terminal status; semantic fixes use fail --counter semantic",
    }


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise MetricsError(f"Metrics artifact already exists (write-once): {path}")
    fd, name = tempfile.mkstemp(prefix=".metrics-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise MetricsError(f"Metrics artifact already exists (write-once): {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def finalize_conversion_metrics(concept: str, *, run: int, session_ids: Sequence[str], artifact_root: Optional[str | Path] = None, opencode_db: Optional[str | Path] = None) -> Path:
    if run < 1:
        raise MetricsError("--run must be >= 1")
    controller = ConversionController(artifact_root=artifact_root)
    if concept not in controller.dag_concepts:
        raise MetricsError(f"Concept {concept!r} is not present in the conversion DAG")
    state = controller._read_state(concept)  # noqa: SLF001
    if state is None:
        raise MetricsError(f"Concept {concept!r} has no current ConversionState")
    if state.status not in TERMINAL_STATUSES:
        raise MetricsError(f"Cannot finalize metrics for {concept!r}: current status is {state.status}; only terminal statuses are accepted")
    output = controller.artifact_root / "mimic-iv/concepts_fhir/metrics" / concept / f"run_{run:04d}.json"
    if output.exists():
        raise MetricsError(f"Metrics artifact already exists (write-once): {output}")
    db_path = Path(opencode_db or "~/.local/share/opencode/opencode.db").expanduser().resolve()
    if not db_path.is_file():
        raise MetricsError(f"OpenCode database not found: {db_path}")
    db = sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        tables = _check_schema(db)
        sessions, roots = _scope_sessions(db, session_ids, controller.artifact_root.resolve())
        session_ids = sorted(row["id"] for row in sessions)
        messages, parts = _scoped_data(db, session_ids)
    finally:
        db.close()
    agents = {row["id"]: (_text(row["agent"]) or "unknown") for row in sessions}
    token_metrics, model_list, versions = _token_metrics(sessions)
    busy, busy_by_agent, message_counts = _message_metrics(messages, agents)
    # Scope the run to the attempts it actually produced. Attempt directories
    # accumulate on disk across a `reopen`, and the three state counters are
    # cumulative, so an unscoped read would bill this run for a previous run's
    # attempts, judge invocations and HPC seconds -- work whose own metrics
    # artifact is already written, making the same run appear in both and any
    # sum over runs an overcount. `run_baseline` is all zeroes on a concept that
    # was never reopened, which leaves the single-run case exactly as it was.
    baseline = state.run_baseline
    all_attempt_dirs = _attempt_dirs(controller, concept)
    attempt_dirs = [item for item in all_attempt_dirs if item[0] > baseline["attempt"]]
    attempt_summaries, jobs, latest_comparison = _attempt_metrics(attempt_dirs)
    poll_by_job, unmatched_polls = _poll_intervals(parts, set(session_ids), concept, jobs)
    poll_intervals = [item for values in poll_by_job.values() for item in values]
    busy_seconds, poll_overlap, submitted_jobs = _duration(busy), _overlap(busy, poll_intervals), len(jobs)
    hpc_accounted_seconds = sum(float(job["runtime_seconds"] or 0) for job in jobs)
    public_jobs = []
    for index, job in enumerate(jobs):
        intervals = poll_by_job.get(index, [])
        public_jobs.append({
            "attempt": job["attempt"], "job_id_present": job["job_id"] is not None,
            "full_result_present": job["full_result_present"], "poll_interval_discoverable": bool(intervals),
            "poll_interval_count": len(_union(intervals)), "actual_poll_interval_seconds": _round(_duration(intervals)),
            "accounting_present": job["accounting_present"],
            "runtime_seconds": _round(job["runtime_seconds"]), "runtime_source": job["runtime_source"],
        })
    per_stage = {}
    for agent in sorted(set(agents.values()) | set(busy_by_agent)):
        usage = _zero_tokens()
        for row in sessions:
            if agents[row["id"]] == agent:
                usage = _add_tokens(usage, _tokens(row))
        per_stage[agent] = {
            "session_count": sum(agents[row["id"]] == agent for row in sessions),
            "tokens": usage, "completed_assistant_messages": len(busy_by_agent.get(agent, [])),
            "duration_seconds": _round(_duration(busy_by_agent.get(agent, []))),
        }
    root_times = [_epoch_ms(row["time_created"]) for row in sessions if row["id"] in roots]
    root_times = [value for value in root_times if value is not None]
    elapsed_time, elapsed_source = _iso_epoch(state.completed_at), "state.completed_at"
    if elapsed_time is None:
        elapsed_time = _iso_epoch(state.updated_at)
        elapsed_source = "state.updated_at" if elapsed_time is not None else None
    elapsed = elapsed_time - min(root_times) if root_times and elapsed_time is not None else None
    attempts_total = max(state.attempt - baseline["attempt"], len(attempt_dirs))
    comparison_rounds = sum((directory / "comparison.full.json").is_file() for _, directory in attempt_dirs)
    judge_invocations = sum((directory / "evidence" / "equivalence-judge.md").is_file() for _, directory in attempt_dirs)
    node = controller.dag_raw["nodes"][concept]
    semantic = _semantic_metrics(state.status, state.semantic_counter - baseline["semantic"])
    artifact = {
        "format_version": "2.0", "schema_version": METRICS_SCHEMA_VERSION, "concept": concept, "run": run,
        "terminal_status": state.status, "terminal_outcome": state.status,
        "session_scope": {"root_session_count": len(roots), "included_session_count": len(sessions), "session_resumptions": max(0, len(roots) - 1)},
        "session_resumptions": max(0, len(roots) - 1), "tokens": token_metrics,
        "runtime": {
            "seconds": _round(max(0.0, busy_seconds - poll_overlap) + hpc_accounted_seconds),
            "method": (
                "union completed assistant-message intervals across all included sessions; "
                "subtract overlap from discovered hpc-poll tool intervals; "
                "add measured HPC runtime from Slurm accounting, falling back to "
                "run_meta execute+compare timings when accounting is unavailable"
            ),
            "busy_union_seconds": _round(busy_seconds), "hpc_poll_overlap_seconds": _round(poll_overlap),
            "hpc_accounted_seconds": _round(hpc_accounted_seconds),
            "hpc_jobs_with_slurm_accounting": sum(job["runtime_source"] == "slurm_sacct_elapsed" for job in jobs),
            "hpc_jobs_with_run_meta_fallback": sum(job["runtime_source"] == "run_meta_execute_compare" for job in jobs),
            "hpc_jobs_without_runtime": sum(job["runtime_source"] is None for job in jobs),
            "hpc_poll_intervals_discovered": len(_union(poll_intervals)), "hpc_poll_intervals_unmatched": unmatched_polls,
            "hpc_jobs_submitted": submitted_jobs,
            "hpc_jobs_without_discoverable_poll_interval": sum(not job["poll_interval_discoverable"] for job in public_jobs),
            "assistant_messages": message_counts, "incomplete_messages_excluded": message_counts["incomplete_assistant_messages"],
            "invalid_message_intervals_excluded": message_counts["invalid_assistant_intervals"], "time_updated_fallback_used": False,
            "actual_elapsed_seconds": _round(elapsed), "actual_elapsed_secondary": True,
            "actual_elapsed_timestamp_source": elapsed_source,
        },
        "per_stage": per_stage,
        "per_attempt": {"attempts_total": attempts_total, "usage_attribution": "unavailable", "attempts": attempt_summaries},
        "convergence": {
            "attempts_total": attempts_total, **semantic,
            "engineering_counter": state.engineering_counter - baseline["engineering"],
            "hpc_counter": state.hpc_counter - baseline["hpc"],
            "submitted_jobs": submitted_jobs, "full_validation_rounds": comparison_rounds,
            "judge_invocations": judge_invocations, "divergence_decided_by": state.divergence_decided_by,
            "human_manual_override": state.divergence_decided_by == "human", "terminal_outcome": state.status,
        },
        # Every number under `convergence`, `per_attempt`, `hpc_jobs` and
        # `runtime` above describes THIS run only. The cumulative figures live
        # here, and the two are reported separately and never summed across
        # runs -- the same discipline the status report applies to COMPLETED vs
        # COMPLETED_WITH_DIVERGENCE, for the same reason: a reader who cannot
        # tell one run's cost from a concept's total cost is being handed a
        # number that means neither.
        "run_scope": {
            "run": run,
            "reopen_count": state.reopen_count,
            "attempt_window": {"after": baseline["attempt"], "through": state.attempt},
            "attempts_this_run": attempts_total,
            "attempts_all_runs": max(state.attempt, len(all_attempt_dirs)),
            "attempt_dirs_excluded": len(all_attempt_dirs) - len(attempt_dirs),
            "cumulative_counters": {
                "semantic": state.semantic_counter,
                "engineering": state.engineering_counter,
                "hpc": state.hpc_counter,
            },
            "reopen_history": state.reopen_history,
        },
        "hpc_jobs": public_jobs, "final_comparator": latest_comparison, "human_interventions": None,
        "human_interventions_reason": "Stored OpenCode data cannot reliably distinguish human messages from plugin/orchestrator continuation messages.",
        "provenance": {
            "source_sql_path": f"mimic-iv/concepts/{node['path']}", "dag_sha256": node["sha256"],
            "tracker_schema_version": TRACKER_SCHEMA_VERSION,
            "opencode_source": {"kind": "sqlite", "filename": db_path.name, "tables": sorted(name for name in ("message", "part", "project", "session") if name in tables)},
            "opencode_versions": versions, "agents": sorted(set(agents.values())), "agent_model_list": model_list,
            "config_hashes": _config_hashes(controller.artifact_root),
            "root_session_count": len(roots), "semantic_rework_method": semantic["semantic_rework_method"],
            "semantic_rework_source": semantic["semantic_rework_source"], "finalized_before_terminal_response": True,
        },
    }
    _atomic_write(output, json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return output


__all__ = ["METRICS_SCHEMA_VERSION", "MetricsError", "finalize_conversion_metrics"]
