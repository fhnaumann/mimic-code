"""Export a ``mimiciv_derived`` concept table as a deterministic JSON oracle artifact.

Reads exactly one table ``mimiciv_derived.<concept>`` from a **read-only**
DuckDB connection, validates that *concept* is a recognised stem in the
concept DAG, and serialises every row into a JSON-safe representation.

Output artifact::

    {
      "format_version": "1.0",
      "concept": "<concept>",
      "dataset": "<label>",
      "columns": ["col_a", "col_b", ...],
      "column_types": {"col_a": "INTEGER", "col_b": "VARCHAR", ...},
      "row_count": 42,
      "exported_at": "2025-08-05T12:34:56Z",
      "source": {"engine": "duckdb", "version": "1.5.5",
                 "path": "/...", "sha256": "..."},
      "rows": [[val_a1, val_b1, ...], ...]
    }

``column_types`` carries DuckDB logical type names; ``compare-port-results``
normalises them against Spark/Pathling names, so no translation happens here.

Exported rows are JSON-safe: ``None``, ``bool``, ``int``, ``float``,
``str`` (dates/times/timestamps in ISO-8601; ``Decimal`` as string to
preserve precision; ``bytes`` as base64; ``NaN`` / ``Inf`` / ``-Inf`` as the
strings ``"NaN"`` / ``"Infinity"`` / ``"-Infinity"``).

Rows are sorted by their canonical JSON encoding, so the artifact does not
depend on scan order.  The artifact is **write-once** — an existing output
path is an error.

Scale note: this serialises the whole table into one JSON document, which is
right for the ~10^2-10^5 row demo build and wrong for full MIMIC-IV.  The
full-data path must compare through aggregates, not whole-table JSON.
"""

from __future__ import annotations

import base64
import json
import math
import re
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

from mimic_utils.duckdb_oracle import (
    DERIVED_SCHEMA,
    OracleError,
    connect_read_only,
    describe_columns,
    duckdb_version,
    file_sha256,
    resolve_duckdb_path,
)

# ---------------------------------------------------------------------------
# Identifier / DAG validation
# ---------------------------------------------------------------------------


def _sanitise_identifier(name: str) -> str:
    """Reject any table / column name that is not a safe SQL identifier."""
    if not name or len(name) > 63:
        raise ValueError(f"Invalid identifier: {name!r}")
    if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


def _validate_concept_in_dag(concept: str, repo_root: Path) -> str:
    """Verify *concept* appears in the DAG ``nodes`` dict; return its stem."""
    dag_path = repo_root / "mimic-iv" / "concept_dag" / "concept_dag.json"
    if not dag_path.exists():
        raise FileNotFoundError(f"DAG artifact not found: {dag_path}")
    dag = json.loads(dag_path.read_text(encoding="utf-8"))
    nodes = dag.get("nodes", {})
    stem = concept.lower()
    if stem not in nodes:
        raise ValueError(
            f"Concept '{concept}' is not a recognised stem in the concept DAG. "
            f"Available: {sorted(nodes.keys())}"
        )
    return stem


# ---------------------------------------------------------------------------
# Row serialisation
# ---------------------------------------------------------------------------


def _serialise_value(val: Any) -> Any:
    """Convert a single DuckDB value to a JSON-safe Python object."""
    if val is None:
        return None
    if isinstance(val, bool):
        # bool is a subclass of int, so test bool first
        return val
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        if math.isnan(val):
            return "NaN"
        if math.isinf(val):
            return "Infinity" if val > 0 else "-Infinity"
        return val
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.isoformat()
        return val.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(val, date):
        return val.isoformat()
    if isinstance(val, time):
        return val.isoformat()
    if isinstance(val, timedelta):
        return _iso_duration(val)
    if isinstance(val, (bytes, memoryview, bytearray)):
        return base64.b64encode(bytes(val)).decode("ascii")
    if isinstance(val, str):
        return val
    if isinstance(val, (list, tuple)):
        return [_serialise_value(v) for v in val]
    if isinstance(val, dict):
        return {str(k): _serialise_value(v) for k, v in val.items()}
    # DuckDB can hand back UUID and other object types; stringify as a last resort.
    return str(val)


def _iso_duration(val: timedelta) -> str:
    """Serialise a timedelta as an ISO-8601 duration string."""
    total = val.total_seconds()
    sign = "-" if total < 0 else ""
    total = abs(total)
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, seconds = divmod(rem, 60)

    parts = [sign, "P"]
    if days:
        parts.append(f"{int(days)}D")
    time_parts: List[str] = []
    if hours:
        time_parts.append(f"{int(hours)}H")
    if minutes:
        time_parts.append(f"{int(minutes)}M")
    if seconds or not time_parts:
        sec_str = f"{seconds:.6f}".rstrip("0").rstrip(".")
        time_parts.append(f"{sec_str}S")
    parts.append("T")
    parts.extend(time_parts)
    return "".join(parts)


def serialise_rows(rows: Any) -> List[list]:
    """Serialise an iterable of row tuples into deterministic JSON-safe lists."""
    out = [[_serialise_value(v) for v in row] for row in rows]
    out.sort(key=lambda row: json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    return out


def write_artifact(artifact: Dict[str, Any], output_path: str | Path) -> Path:
    """Write *artifact* to *output_path* write-once, via a temp file + rename."""
    output_path = Path(output_path).resolve()
    if output_path.exists():
        raise FileExistsError(
            f"Output artifact already exists (write-once): {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        tmp_path.write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
        tmp_path.rename(output_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
    return output_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def export_oracle(
    concept: str,
    output_path: str | Path,
    *,
    duckdb_path: Optional[str | Path] = None,
    dataset: str = "demo",
    repo_root: Optional[Path] = None,
) -> Path:
    """Export ``mimiciv_derived.<concept>`` to a deterministic JSON artifact.

    Parameters
    ----------
    concept:
        The DAG concept stem (e.g. ``"age"``).  Validated against the DAG.
    output_path:
        JSON file path to write.  Must **not** exist (write-once).
    duckdb_path:
        DuckDB oracle path.  Resolved from ``MIMIC_DUCKDB_PATH`` or the
        built-in default when ``None``.  Always opened read-only.
    dataset:
        Human-readable label recorded in the artifact (default ``"demo"``).
    repo_root:
        Project root for DAG lookup.  Auto-detected when ``None``.

    Returns
    -------
    The resolved output path.

    Raises
    ------
    FileExistsError
        If *output_path* already exists.
    ValueError
        If *concept* is not in the DAG or is an unsafe identifier.
    RuntimeError
        On oracle access or query errors.
    """
    output_path = Path(output_path).resolve()
    if output_path.exists():
        raise FileExistsError(
            f"Output artifact already exists (write-once): {output_path}"
        )

    if repo_root is None:
        repo_root = Path(__file__).resolve().parent.parent.parent

    stem = _validate_concept_in_dag(concept, repo_root)
    _sanitise_identifier(stem)

    resolved = resolve_duckdb_path(duckdb_path)

    try:
        with connect_read_only(resolved) as con:
            column_types = describe_columns(con, DERIVED_SCHEMA, stem)
            if not column_types:
                raise RuntimeError(
                    f"Table {DERIVED_SCHEMA}.{stem} not found in {resolved}"
                )
            cur = con.execute(f'SELECT * FROM "{DERIVED_SCHEMA}"."{stem}"')
            columns = [d[0] for d in cur.description]
            rows_raw = cur.fetchall()
    except OracleError as exc:
        raise RuntimeError(str(exc)) from exc
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Export error for concept '{stem}': {exc}") from exc

    # information_schema and the cursor must agree on column order/naming.
    if columns != list(column_types.keys()):
        column_types = {col: column_types.get(col, "UNKNOWN") for col in columns}

    rows_serialised = serialise_rows(rows_raw)

    artifact: Dict[str, Any] = {
        "format_version": "1.0",
        "concept": stem,
        "dataset": dataset,
        "columns": columns,
        "column_types": column_types,
        "row_count": len(rows_serialised),
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "engine": "duckdb",
            "version": duckdb_version(),
            "path": str(resolved),
            "sha256": file_sha256(resolved),
            "table": f"{DERIVED_SCHEMA}.{stem}",
        },
        "rows": rows_serialised,
    }

    return write_artifact(artifact, output_path)
