"""Minimal Pathling HTTP adapter for the concept-port loop.

A deliberately small stdlib-only client covering exactly the three
operations the loop needs, in the forms proven by
``../master_thesis_pipeline/orchestration-new/src/services/pathling_client.py``
and ``scripts/sofa_provisioning/register_patient_sofa.py``:

- ``capability_statement()`` — ``GET /metadata``.
- ``put_definitional()`` — PUT-by-id upsert of a ViewDefinition or Library.
  HAPI requires the body ``id`` to equal the URL id, so it is set here.
- ``sqlquery_run_sync()`` — ``POST /$sqlquery-run`` with a ``Parameters``
  body carrying ``queryResource`` (an inline sql-query Library) and
  ``_format = ndjson``, requested with ``Accept: application/x-ndjson``.

Three details are easy to get wrong and are fixed here:

1. ``$sqlquery-run`` takes a **Parameters** resource, not a bare Library.
2. The Library ``type`` coding system is
   ``https://sql-on-fhir.org/ig/CodeSystem/LibraryTypesCodes`` (the
   SQL-on-FHIR IG), not the HL7 ``library-type`` CodeSystem.
3. Each ``relatedArtifact`` needs **both** ``label`` (the SQL table name)
   and ``resource`` (the canonical URL).  ``$sqlquery-run`` has no ambient
   table namespace: a table is only visible if its definition is carried as
   a ``depends-on`` relatedArtifact.

TLS uses the default verifying context.  Verification is never disabled;
the local dev server is plain HTTP and needs no TLS configuration at all.
An optional bearer token can be supplied via ``PATHLING_TOKEN`` for a
protected endpoint; full OAuth2 client-credentials flow is out of scope and
lives in the external pipeline's client.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL_ENV_KEY = "PATHLING_FHIR_BASE_URL"
DEFAULT_BASE_URL = "http://localhost:8080/fhir/"
TOKEN_ENV_KEY = "PATHLING_TOKEN"

# SQL-on-FHIR IG Library type coding — the coding Pathling recognises.
LIBRARY_TYPE_SYSTEM = "https://sql-on-fhir.org/ig/CodeSystem/LibraryTypesCodes"
LIBRARY_KIND_SQL_QUERY = "sql-query"
LIBRARY_KIND_SQL_VIEW = "sql-view"

DEFAULT_TIMEOUT = 60.0
QUERY_TIMEOUT = 900.0


class PathlingError(RuntimeError):
    """Any failed Pathling interaction, with the server's diagnostic attached."""


def resolve_base_url(explicit: Optional[str] = None) -> str:
    """Resolve the FHIR base URL from *explicit* -> env -> default, trailing slash."""
    raw = explicit or os.environ.get(BASE_URL_ENV_KEY, DEFAULT_BASE_URL)
    return raw.rstrip("/") + "/"


@dataclass(frozen=True)
class RelatedArtifact:
    """A ``depends-on`` dependency: SQL table *label* -> canonical *resource*."""

    label: str
    resource: str

    def as_fhir(self) -> Dict[str, str]:
        return {"type": "depends-on", "label": self.label, "resource": self.resource}


def build_sqlquery_library(
    sql: str,
    related_artifacts: Sequence[RelatedArtifact] = (),
    *,
    kind: str = LIBRARY_KIND_SQL_QUERY,
    url: Optional[str] = None,
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a Library conforming to the SQL-on-FHIR SQLQuery profile.

    *kind* is ``sql-query`` for an inline one-shot execution, or ``sql-view``
    for a stored compute-on-read table (which then needs a ``url``).
    """
    encoded = base64.b64encode(sql.encode("utf-8")).decode("ascii")
    library: Dict[str, Any] = {
        "resourceType": "Library",
        "status": "active",
        "type": {"coding": [{"system": LIBRARY_TYPE_SYSTEM, "code": kind}]},
        "content": [{"contentType": "application/sql", "data": encoded}],
        "relatedArtifact": [a.as_fhir() for a in related_artifacts],
    }
    if url is not None:
        library["url"] = url
    if name is not None:
        library["name"] = name
    return library


class PathlingClient:
    """Stdlib HTTP client for the Pathling operations the port loop uses."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        token: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        query_timeout: float = QUERY_TIMEOUT,
    ) -> None:
        self.base_url = resolve_base_url(base_url)
        self.token = token if token is not None else os.environ.get(TOKEN_ENV_KEY)
        self.timeout = timeout
        self.query_timeout = query_timeout

    # -- internals ---------------------------------------------------------

    def _headers(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {"Accept": "application/fhir+json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[dict] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> Tuple[int, str]:
        """Issue a request and return ``(status, body_text)``.

        Raises :class:`PathlingError` on transport failure or any status >= 400,
        including the server's response snippet — an OperationOutcome
        ``diagnostics`` string is usually the whole diagnosis.
        """
        url = path if path.startswith("http") else self.base_url + path.lstrip("/")
        data: Optional[bytes] = None
        merged = self._headers(headers)
        if json_body is not None:
            data = json.dumps(json_body, ensure_ascii=False).encode("utf-8")
            merged.setdefault("Content-Type", "application/fhir+json")

        req = Request(url, data=data, headers=merged, method=method)
        try:
            with urlopen(req, timeout=timeout or self.timeout) as resp:
                return resp.status, resp.read().decode("utf-8")
        except HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                pass
            raise PathlingError(
                f"{method} {url} -> HTTP {exc.code}: {_diagnostic(body)}"
            ) from exc
        except URLError as exc:
            raise PathlingError(f"{method} {url} -> transport failure: {exc.reason}") from exc

    # -- operations --------------------------------------------------------

    def capability_statement(self) -> Dict[str, Any]:
        """``GET /metadata`` -> the parsed CapabilityStatement."""
        _, body = self._request("GET", "metadata")
        return json.loads(body)

    def put_definitional(
        self,
        *,
        resource_type: str,
        resource_id: str,
        resource_body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """PUT-by-id upsert of a ViewDefinition or Library (create and overwrite).

        PUT is idempotent in Pathling; DELETE explicitly is not, so the loop
        only ever upserts.
        """
        body = {**resource_body, "id": resource_id}
        _, text = self._request(
            "PUT", f"{resource_type}/{resource_id}", json_body=body
        )
        return json.loads(text) if text else {}

    def sqlquery_run_sync(
        self,
        sql: str,
        related_artifacts: Sequence[RelatedArtifact] = (),
    ) -> Tuple[List[str], List[List[Any]]]:
        """Execute *sql* synchronously and return ``(columns, rows)``.

        Column order is recovered from the first NDJSON object's key order.
        A query returning zero rows yields ``([], [])`` — the caller decides
        whether that is a failure.
        """
        params = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "queryResource",
                    "resource": build_sqlquery_library(sql, related_artifacts),
                },
                {"name": "_format", "valueCode": "ndjson"},
            ],
        }
        _, body = self._request(
            "POST",
            "$sqlquery-run",
            json_body=params,
            headers={"Accept": "application/x-ndjson"},
            timeout=self.query_timeout,
        )
        return parse_ndjson(body)

    def sqlquery_run_dicts(
        self,
        sql: str,
        related_artifacts: Sequence[RelatedArtifact] = (),
    ) -> List[Dict[str, Any]]:
        """Execute *sql* and return each NDJSON row as its own dict.

        Preferred over :meth:`sqlquery_run_sync` when a null-valued column may
        be omitted from a row object: the caller supplies the authoritative
        column order (from ``DESCRIBE``) instead of inferring it from row 1.
        """
        params = {
            "resourceType": "Parameters",
            "parameter": [
                {
                    "name": "queryResource",
                    "resource": build_sqlquery_library(sql, related_artifacts),
                },
                {"name": "_format", "valueCode": "ndjson"},
            ],
        }
        _, body = self._request(
            "POST",
            "$sqlquery-run",
            json_body=params,
            headers={"Accept": "application/x-ndjson"},
            timeout=self.query_timeout,
        )
        return parse_ndjson_dicts(body)

    def describe_columns(
        self,
        table: str,
        related_artifacts: Sequence[RelatedArtifact] = (),
    ) -> Dict[str, str]:
        """``DESCRIBE <table>`` -> ``{column_name: spark_type}`` in declared order."""
        columns, rows = self.sqlquery_run_sync(f"DESCRIBE {table}", related_artifacts)
        if "col_name" not in columns or "data_type" not in columns:
            raise PathlingError(
                f"DESCRIBE {table} returned unexpected shape: {columns}"
            )
        name_idx = columns.index("col_name")
        type_idx = columns.index("data_type")
        described: Dict[str, str] = {}
        for row in rows:
            name = row[name_idx]
            # Spark's DESCRIBE appends partition-info sections with blank or
            # '#'-prefixed marker rows; neither is a real column.
            if not name or str(name).startswith("#"):
                continue
            described[str(name)] = str(row[type_idx])
        return described


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_ndjson_dicts(body: str) -> List[Dict[str, Any]]:
    """Parse an NDJSON response into one dict per row, keys as returned."""
    rows: List[Dict[str, Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise PathlingError(f"NDJSON row is not a JSON object: {obj!r}")
        rows.append(obj)
    return rows


def parse_ndjson(body: str) -> Tuple[List[str], List[List[Any]]]:
    """Parse an NDJSON response into ``(columns, rows)``.

    Column order comes from the first row's key order (JSON objects preserve
    insertion order), so downstream consumers never guess dict iteration
    order.  An empty body yields no columns and no rows.
    """
    columns: List[str] = []
    rows: List[List[Any]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise PathlingError(f"NDJSON row is not a JSON object: {obj!r}")
        if not columns:
            columns = list(obj.keys())
        rows.append([obj.get(c) for c in columns])
    return columns, rows


def _diagnostic(body: str) -> str:
    """Pull an OperationOutcome diagnostic out of an error body, else truncate."""
    if not body:
        return "(empty response)"
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return body[:500]
    if isinstance(parsed, dict) and parsed.get("resourceType") == "OperationOutcome":
        details = []
        for issue in parsed.get("issue", []):
            text = issue.get("diagnostics") or issue.get("details", {}).get("text")
            if text:
                details.append(str(text))
        if details:
            return " | ".join(details)[:1000]
    return body[:500]


def capability_summary(capability_statement: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the facts the preflight gates on from a CapabilityStatement."""
    rest = capability_statement.get("rest", []) or []
    resource_types = {
        res.get("type", "")
        for entry in rest
        for res in (entry.get("resource", []) or [])
    }
    operations = {
        op.get("name", "")
        for entry in rest
        for op in (entry.get("operation", []) or [])
    }
    software = capability_statement.get("software", {}) or {}
    return {
        "resource_type": capability_statement.get("resourceType", ""),
        "fhir_version": capability_statement.get("fhirVersion", ""),
        "software_name": software.get("name", ""),
        "software_version": software.get("version", "")
        or capability_statement.get("version", ""),
        "resource_types": resource_types,
        "operations": operations,
    }
