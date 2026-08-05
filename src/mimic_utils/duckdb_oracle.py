"""Shared read-only DuckDB access for the concept-port loop.

The local source-of-truth oracle for the concept port is a single DuckDB
file built from MIMIC-IV 2.2 demo data.  Every code path in the loop opens
it with ``read_only=True`` — the loop must never be able to mutate the
oracle it is validating against.

Path resolution order
---------------------
1. explicit argument (``--duckdb PATH``)
2. ``MIMIC_DUCKDB_PATH`` environment variable
3. built-in default ``/Users/nau025/warehouses/mimic4-demo.db``

DuckDB has no roles, so there is no server-side ``mimic_ro`` equivalent and
no ``SHOW transaction_read_only`` to assert.  Read-only is a property of the
*connection*, which is why :func:`connect_read_only` is the only sanctioned
way in this package to open the oracle.
"""

from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

# duckdb exposed at module level so tests can monkeypatch it.
try:
    import duckdb as duckdb  # noqa: F811
except ImportError:  # pragma: no cover - duckdb ships with both extras
    duckdb = None  # type: ignore[assignment]

ENV_KEY = "MIMIC_DUCKDB_PATH"
DEFAULT_DUCKDB_PATH = "/Users/nau025/warehouses/mimic4-demo.db"

# Schemas the MIMIC-IV 2.2 DuckDB demo build is expected to contain.
REQUIRED_SCHEMAS = ("mimiciv_hosp", "mimiciv_icu", "mimiciv_derived")

DERIVED_SCHEMA = "mimiciv_derived"


class OracleError(RuntimeError):
    """Raised when the DuckDB oracle is missing or cannot be opened read-only."""


def resolve_duckdb_path(explicit: Optional[str | Path] = None) -> Path:
    """Resolve the oracle path from *explicit* -> env -> built-in default."""
    if explicit:
        return Path(explicit).expanduser()
    return Path(os.environ.get(ENV_KEY, DEFAULT_DUCKDB_PATH)).expanduser()


@contextmanager
def connect_read_only(path: Optional[str | Path] = None) -> Iterator[Any]:
    """Open the DuckDB oracle read-only and always close it.

    Raises :class:`OracleError` when duckdb is unavailable, the file is
    missing, or the connection cannot be established.  A missing file is
    reported explicitly because ``duckdb.connect`` in read-only mode fails
    with a less obvious message.
    """
    if duckdb is None:
        raise OracleError(
            "duckdb is not installed; install with the [equivalence] extra"
        )

    resolved = resolve_duckdb_path(path)
    if not resolved.exists():
        raise OracleError(f"DuckDB oracle file not found: {resolved}")
    if not resolved.is_file():
        raise OracleError(f"DuckDB oracle path is not a file: {resolved}")

    try:
        con = duckdb.connect(str(resolved), read_only=True)
    except Exception as exc:  # duckdb.Error subclasses vary by version
        raise OracleError(f"Cannot open {resolved} read-only: {exc}") from exc

    try:
        yield con
    finally:
        try:
            con.close()
        except Exception:
            pass


def file_sha256(path: str | Path, *, chunk_size: int = 1 << 20) -> str:
    """SHA-256 of the oracle file — the identity recorded in every artifact."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duckdb_version() -> str:
    """Installed DuckDB Python package version, or ``"unavailable"``."""
    if duckdb is None:
        return "unavailable"
    return getattr(duckdb, "__version__", "unknown")


def list_schemas(con: Any) -> list[str]:
    """User schemas present in the database, sorted."""
    rows = con.execute(
        "SELECT DISTINCT table_schema FROM information_schema.tables "
        "ORDER BY table_schema"
    ).fetchall()
    return [r[0] for r in rows]


def list_tables(con: Any, schema: str) -> list[str]:
    """Table names in *schema*, sorted."""
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = ? ORDER BY table_name",
        [schema],
    ).fetchall()
    return [r[0] for r in rows]


def describe_columns(con: Any, schema: str, table: str) -> dict[str, str]:
    """``{column_name: duckdb_type}`` for *schema.table*, in ordinal order.

    Uses ``information_schema.columns`` rather than ``DESCRIBE`` so the
    schema/table pair can be passed as bound parameters instead of being
    interpolated into SQL.
    """
    rows = con.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = ? AND table_name = ? ORDER BY ordinal_position",
        [schema, table],
    ).fetchall()
    return {name: dtype for name, dtype in rows}
