"""Register exported concept artifacts on a SQL-on-FHIR server.

Walks ``mimic-iv/concepts_fhir/artifacts``, ``PUT``s each concept's
ViewDefinitions and then its Library, reads every resource back, and runs one
smoke query per concept.  The point is to make a concept referenceable *by
name*: once its Library is registered, downstream work names
``https://fhnaumann.masters/pathling/Library/<concept>`` and the server resolves
the SQL, its ViewDefinitions, and any Library it reads.

Three server behaviours this leans on, each established by probing a live
Pathling 3.0.0 instance rather than read off a spec:

* ``PUT <type>/<id>`` is an idempotent upsert (HTTP 200 on re-run).  Every id is
  deterministic and collision-free by construction -- ``age``, ``age-patient``,
  ``charlson-condition`` -- so the id *is* the identity and re-running is always
  safe.  That is what lets this module skip staging, rollback and
  skip-if-unchanged entirely.
* Resources round-trip byte-identically apart from a server-added ``meta``.
  Read-back can therefore be exact equality modulo ``meta``, which is both
  simpler than a curated field list and empirically free of false positives --
  which in turn is what makes it safe to treat a mismatch as fatal.
* Nothing is validated referentially at write time: a Library whose
  ``depends-on`` names a resource that does not exist is accepted with a 200 and
  fails later, at query time, with an error naming the wrong concept.  Upload
  order therefore does not affect whether a write *succeeds*, but it decides
  whether the smoke test tells the truth, so dependencies go first.

Exit contract: ``2`` for anything that stops the run before it starts (bad
config, missing secret, token rejected), ``1`` for a failed write or a read-back
mismatch, and ``0`` otherwise -- *including* when every smoke test failed.  A
smoke failure is reported loudly and never changes the exit code, because
executing a view exercises a different system than registering one, and today
two known upstream Pathling bugs (aehrc/pathling#2730, #2731) make some
correctly-registered concepts unrunnable.  A gate that is permanently red gets
ignored, then bypassed, then deleted.  Promote smoke to fatal once those land.

Two artifacts currently carry a hand-applied workaround for those bugs that
``export-mappings`` reverts -- see ``mimic-iv/concepts_fhir/PATHLING_WORKAROUNDS.md``.
The smoke test is what catches a lapse.
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from typing import Iterable, Optional, Sequence, Union

import sqlglot
from sqlglot import exp

from mimic_utils.export_mappings import (
    DEFAULT_EXPORT_DIR,
    LIBRARY_BASE,
    SQL_DIALECT,
    VIEWDEFINITION_GLOB,
    VIEWDEFINITION_PREFIX,
)
from mimic_utils.pathling_config import (
    QUERY_TIMEOUT,
    PathlingEnv,
    build_client,
    load_pathling_env,
)

# src/mimic_utils/artifact_upload.py -> src -> repo root.  `DEFAULT_EXPORT_DIR`
# is repo-relative, and this command is run by hand from wherever the developer
# happens to be standing, so it is anchored rather than resolved against the CWD.
_REPO_ROOT = Path(__file__).resolve().parents[2]

#: Server-managed metadata.  The only key Pathling adds on the way in, and the
#: only one read-back ignores.
_SERVER_MANAGED = ("meta",)

#: One row is enough to prove the view resolves and to read its column names;
#: asking for more only costs query time on a full-size dataset.
_SMOKE_LIMIT = 1


class RegistrationError(Exception):
    """A write failed, or a resource did not read back as it was sent."""


@dataclass
class ConceptArtifact:
    """One concept directory: the resources to register and what to expect back."""

    concept: str
    directory: Path
    library_path: Path
    library: dict
    #: ``(path, resource)`` for each ViewDefinition, in upload order.
    viewdefs: list[tuple[Path, dict]] = field(default_factory=list)
    #: Concepts whose *Library* this one reads, e.g. ``charlson`` -> ``age``.
    library_deps: tuple[str, ...] = ()

    @property
    def canonical(self) -> str:
        return self.library["url"]

    def resources(self) -> list[tuple[str, str, dict]]:
        """``(resourceType, id, body)`` with ViewDefinitions before the Library.

        The Library goes last so that an interrupted run leaves the *previous*
        Library pointing at resources that exist, rather than a new one pointing
        at ViewDefinitions that were never written.
        """
        out = [("ViewDefinition", vd["id"], vd) for _, vd in self.viewdefs]
        out.append(("Library", self.library["id"], self.library))
        return out

    def expected_columns(self) -> tuple[str, ...]:
        """The outermost projection of the Library's SQL.

        Read from the ``sql-text`` extension -- the authoritative copy the
        server runs, not the readability sidecar beside it.
        """
        sql = self.library["content"][0]["extension"][0]["valueString"]
        try:
            tree = sqlglot.parse_one(sql, dialect=SQL_DIALECT)
        except Exception:
            return ()
        select = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
        if select is None:
            return ()
        return tuple(item.alias_or_name for item in select.expressions)


@dataclass
class SmokeResult:
    """What one ``$sql-run`` said.  Never fatal -- see the module docstring."""

    concept: str
    ok: bool
    status: Optional[int] = None
    rows: int = 0
    columns: tuple[str, ...] = ()
    detail: str = ""

    def line(self) -> str:
        if self.ok:
            return f"    smoke        ok   ({len(self.columns)} column(s), {self.rows} row(s))"
        return f"    smoke        FAILED{'' if self.status is None else f' (HTTP {self.status})'}"


def discover(artifact_root: Union[str, Path]) -> dict[str, ConceptArtifact]:
    """Read every concept bundle under *artifact_root*.

    The directory *is* the set of registerable concepts: ``export-mappings``
    withholds any concept that still projects a MIMIC identifier, so anything
    present here is joinable to FHIR data.  That is why this module needs no
    allowlist of its own -- a second source of truth for readiness would only
    rot.
    """
    root = Path(artifact_root)
    if not root.is_dir():
        raise RegistrationError(f"Artifact directory not found: {root}")

    found: dict[str, ConceptArtifact] = {}
    for library_path in sorted(root.glob("*/*/Library.*.json")):
        directory = library_path.parent
        concept = directory.name
        try:
            library = json.loads(library_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistrationError(f"Cannot read {library_path}: {exc}") from exc
        if library.get("resourceType") != "Library":
            raise RegistrationError(
                f"{library_path} has resourceType {library.get('resourceType')!r}, "
                f"expected 'Library'"
            )
        if concept in found:
            raise RegistrationError(
                f"Concept {concept!r} appears twice: {found[concept].directory} and {directory}"
            )

        viewdefs: list[tuple[Path, dict]] = []
        for path in sorted(directory.glob(VIEWDEFINITION_GLOB)):
            try:
                body = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RegistrationError(f"Cannot read {path}: {exc}") from exc
            viewdefs.append((path, body))
        if not viewdefs:
            raise RegistrationError(f"Concept {concept!r} ships no ViewDefinitions in {directory}")

        deps = tuple(
            sorted(
                related["resource"][len(LIBRARY_BASE) + 1 :]
                for related in library.get("relatedArtifact", [])
                if str(related.get("resource", "")).startswith(LIBRARY_BASE + "/")
            )
        )
        found[concept] = ConceptArtifact(
            concept=concept,
            directory=directory,
            library_path=library_path,
            library=library,
            viewdefs=viewdefs,
            library_deps=deps,
        )
    if not found:
        raise RegistrationError(f"No concept bundles found under {root}")
    return found


def plan(
    artifacts: dict[str, ConceptArtifact],
    concepts: Sequence[str] = (),
    *,
    every: bool = False,
) -> tuple[list[str], set[str]]:
    """Resolve a selection into a dependency-ordered upload list.

    Returns ``(order, added)``, where *added* names the concepts pulled in as
    dependencies rather than asked for.  A concept is uploaded after everything
    it reads, so that a smoke failure means the concept is broken and not merely
    that its dependency was not there yet.
    """
    if every:
        wanted = set(artifacts)
    else:
        unknown = [c for c in concepts if c not in artifacts]
        if unknown:
            raise RegistrationError(
                f"Not registerable: {', '.join(sorted(unknown))}. "
                f"Available: {', '.join(sorted(artifacts))}"
            )
        wanted = set(concepts)

    # Transitive closure over Library dependencies.  Safe to widen the selection
    # silently only because the artifact directory already excludes unready
    # concepts; without that gate this could push something unvetted.
    added: set[str] = set()
    queue = list(wanted)
    while queue:
        concept = queue.pop()
        for dep in artifacts[concept].library_deps:
            if dep not in artifacts:
                raise RegistrationError(
                    f"Concept {concept!r} reads Library {dep!r}, which is not in the "
                    f"artifact directory. Re-run export-mappings."
                )
            if dep not in wanted:
                wanted.add(dep)
                added.add(dep)
                queue.append(dep)

    graph = {c: set(artifacts[c].library_deps) & wanted for c in wanted}
    try:
        order = list(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        raise RegistrationError(f"Library dependencies form a cycle: {exc.args[1]}") from exc
    return order, added


def _strip_server_managed(body: dict) -> dict:
    return {k: v for k, v in body.items() if k not in _SERVER_MANAGED}


def _put_and_verify(client, resource_type: str, rid: str, body: dict, out) -> None:
    """``PUT`` one resource and prove the server stored what we sent.

    A 200 with quietly rewritten content would invalidate the artifact while
    looking like success, so the write is not trusted on its own.
    """
    import httpx

    path = f"{resource_type}/{rid}"
    try:
        resp = client.put(path, json=body, headers={"Content-Type": "application/fhir+json"})
    except httpx.HTTPError as exc:
        raise RegistrationError(f"PUT {path} failed: {exc}") from exc
    if resp.status_code not in (200, 201):
        raise RegistrationError(
            f"PUT {path} returned HTTP {resp.status_code}: {resp.text[:400]}"
        )
    print(f"    PUT {path:<44} {resp.status_code}", file=out)

    try:
        back = client.get(path)
    except httpx.HTTPError as exc:
        raise RegistrationError(f"read-back of {path} failed: {exc}") from exc
    if back.status_code != 200:
        raise RegistrationError(
            f"read-back of {path} returned HTTP {back.status_code}: {back.text[:400]}"
        )
    try:
        stored = back.json()
    except ValueError as exc:
        raise RegistrationError(f"read-back of {path} returned non-JSON: {exc}") from exc

    if _strip_server_managed(stored) != _strip_server_managed(body):
        sent_keys = set(_strip_server_managed(body))
        got_keys = set(_strip_server_managed(stored))
        differing = sorted(
            k for k in sent_keys & got_keys if stored.get(k) != body.get(k)
        )
        raise RegistrationError(
            f"{path} did not read back as sent -- the server rewrote it. "
            f"added={sorted(got_keys - sent_keys)} dropped={sorted(sent_keys - got_keys)} "
            f"changed={differing}"
        )


def smoke(client, artifact: ConceptArtifact) -> SmokeResult:
    """Execute the registered Library once and check the shape it serves.

    CSV, not JSON: ``_format=json`` 500s on any view projecting a timestamp
    (aehrc/pathling#2730/#2731), which ``age`` does via ``admittime``.  The cost
    of that choice is real -- this cannot catch a JSON-serialization regression.

    Row count is reported but never asserted.  A rare concept can legitimately
    return zero rows on a 100-patient demo dataset, so requiring data would fail
    for reasons that have nothing to do with the artifact.
    """
    import httpx

    expected = artifact.expected_columns()
    try:
        resp = client.get(
            "$sql-run",
            params={
                "subjectCanonical": artifact.canonical,
                "_limit": _SMOKE_LIMIT,
                "_format": "csv",
                "header": "true",
            },
            headers={"Accept": "text/csv"},
            timeout=QUERY_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        return SmokeResult(artifact.concept, False, detail=f"request failed: {exc}")

    if resp.status_code != 200:
        detail = resp.text[:1500]
        try:  # a FHIR error carries the useful part in OperationOutcome
            outcome = resp.json()
            issues = outcome.get("issue") or []
            if issues:
                detail = "\n".join(
                    str(i.get("diagnostics") or i.get("code") or "") for i in issues
                )
        except ValueError:
            pass
        return SmokeResult(artifact.concept, False, status=resp.status_code, detail=detail)

    rows = list(csv.reader(io.StringIO(resp.text)))
    rows = [r for r in rows if r]
    if not rows:
        return SmokeResult(
            artifact.concept,
            False,
            status=resp.status_code,
            detail="response carried no header row, so the served columns are unknown",
        )
    columns = tuple(rows[0])
    if expected and columns != expected:
        return SmokeResult(
            artifact.concept,
            False,
            status=resp.status_code,
            rows=len(rows) - 1,
            columns=columns,
            detail=(
                "served columns differ from the Library's SQL projection\n"
                f"  expected: {list(expected)}\n"
                f"  served:   {list(columns)}"
            ),
        )
    return SmokeResult(
        artifact.concept, True, status=resp.status_code, rows=len(rows) - 1, columns=columns
    )


def register_derived_concepts(
    concepts: Iterable[str] = (),
    *,
    every: bool = False,
    env_name: Optional[str] = None,
    config_path: Optional[Union[str, Path]] = None,
    artifact_root: Optional[Union[str, Path]] = None,
    dry_run: bool = False,
    out=None,
) -> int:
    """Register the selected concepts, returning a process exit code."""
    import logging
    import sys

    # httpx logs every request at INFO, which restates the PUT/GET lines printed
    # below and buries the smoke diagnostics between them.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    out = out or sys.stdout
    selection = tuple(concepts)

    env: PathlingEnv = load_pathling_env(path=config_path, env_name=env_name)
    root = (
        Path(artifact_root)
        if artifact_root is not None
        else _REPO_ROOT / DEFAULT_EXPORT_DIR
    )
    artifacts = discover(root)
    order, added = plan(artifacts, selection, every=every)

    print(f"Target: {env.describe()}", file=out)
    print(f"Source: {root}", file=out)
    label = "all ready concepts" if every else "requested"
    print(f"Plan:   {len(order)} concept(s) ({label}): {', '.join(order)}", file=out)
    if added:
        print(
            f"        {', '.join(sorted(added))} added as Library dependenc"
            f"{'y' if len(added) == 1 else 'ies'}",
            file=out,
        )

    if dry_run:
        print("\n--dry-run: nothing was written. Resources that would be sent:", file=out)
        for concept in order:
            for resource_type, rid, _ in artifacts[concept].resources():
                print(f"    PUT {resource_type}/{rid}", file=out)
        return 0

    smoked: list[SmokeResult] = []
    with build_client(env) as client:
        for concept in order:
            artifact = artifacts[concept]
            print(f"\n{concept}", file=out)
            for resource_type, rid, body in artifact.resources():
                _put_and_verify(client, resource_type, rid, body, out)
            print(f"    read-back    ok   (all {len(artifact.resources())} resource(s))", file=out)
            result = smoke(client, artifact)
            smoked.append(result)
            print(result.line(), file=out)
            if not result.ok:
                for line in result.detail.splitlines():
                    print(f"      {line}", file=out)

    failed = [r.concept for r in smoked if not r.ok]
    print(
        f"\nRegistered {len(order)} concept(s) on {env.base_url} "
        f"({len(smoked) - len(failed)}/{len(smoked)} smoke passed).",
        file=out,
    )
    if failed:
        # Loud, specific, and deliberately not fatal -- see the module docstring.
        print(
            f"WARNING: {len(failed)} concept(s) registered but did not execute: "
            f"{', '.join(failed)}.\n"
            f"         They are on the server and referenceable; the failure is in "
            f"running them.\n"
            f"         Known upstream causes: aehrc/pathling#2730, #2731.",
            file=out,
        )
    return 0


__all__ = [
    "ConceptArtifact",
    "RegistrationError",
    "SmokeResult",
    "discover",
    "plan",
    "register_derived_concepts",
    "smoke",
]
