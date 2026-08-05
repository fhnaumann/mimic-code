"""Deterministic static concept DAG generator for mimic-iv/concepts.

Recursively discovers canonical mimic-iv/concepts SQL (excluding concept_map/
and non-SQL files), parses each via sqlglot BigQuery *scope traversal* to
extract physical ``mimiciv_derived`` dependencies while correctly excluding
CTE and subquery aliases, builds a deterministic DAG using Kahn's algorithm,
and emits machine-independent JSON and human-readable Markdown artifacts.

Edge direction: ``{"consumer": A, "dependency": B}`` means concept A depends
on concept B (A's SQL references ``mimiciv_derived.B``).  B must be built
before A.
"""

from __future__ import annotations

import hashlib
import json
import logging
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import Scope, traverse_scope

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CATALOG = "physionet-data"
DERIVED_SCHEMA = "mimiciv_derived"
SOURCE_ROOT_REL = "mimic-iv/concepts"
PARSER_VERSION = f"sqlglot {sqlglot.__version__}"

_DAG_DIR_NAME = "concept_dag"
_JSON_FILE = "concept_dag.json"
_MD_FILE = "concept_dag.md"


# ---------------------------------------------------------------------------
# SQL parsing via scope traversal
# ---------------------------------------------------------------------------

def _parse_sql_deps(sql: str) -> tuple[set[str], set[str], list[str]]:
    """Parse BigQuery SQL using ``traverse_scope`` to extract dependencies.

    For each scope, CTE references are identified via ``scope.sources``
    (entries whose value is a ``Scope`` object).  All remaining ``Table``
    nodes are physical references — they are classified as derived deps,
    raw tables, or ambiguous sources.

    Returns:
        (derived_deps, raw_tables, ambiguous_msgs)
    """
    parsed = sqlglot.parse_one(sql, read="bigquery")

    derived: set[str] = set()
    raw: set[str] = set()
    ambiguous: list[str] = []

    for scope in traverse_scope(parsed):
        # Names that resolve to a CTE (or subquery) in this scope
        scope_cte_refs: set[str] = set()
        for name, source in scope.sources.items():
            if isinstance(source, Scope):
                scope_cte_refs.add(name.lower())

        for table in scope.tables:
            tbl_name = table.name
            if not tbl_name:
                continue
            tbl_lower = tbl_name.lower()

            cat = table.catalog.lower() if table.catalog else None
            db = table.db.lower() if table.db else None

            # --- CTE / subquery alias reference ---
            if cat is None and db is None:
                if tbl_lower in scope_cte_refs:
                    continue
                # Unqualified name that is NOT a CTE - ambiguous
                ambiguous.append(
                    f"Unqualified physical table reference "
                    f"'{tbl_name}' (not a CTE in scope)"
                )
                continue

            # --- Fully qualified with our catalog ---
            if cat == CATALOG:
                if db == DERIVED_SCHEMA:
                    derived.add(tbl_lower)
                elif db is not None:
                    raw.add(f"{db}.{tbl_lower}")
                else:
                    ambiguous.append(
                        f"Table reference has catalog '{CATALOG}' but no "
                        f"schema: '{tbl_name}'"
                    )
                continue

            # --- Has a db but non-standard or missing catalog ---
            if db is not None:
                ambiguous.append(
                    f"Table reference with non-standard catalog or missing "
                    f"catalog: "
                    f"'{'.'.join(filter(None, [cat, db, tbl_name]))}'"
                )
                continue

            # --- Fallthrough ---
            ambiguous.append(
                f"Unclassifiable table reference: '{tbl_name}'"
            )

    return derived, raw, ambiguous


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def discover_concept_files(concepts_dir: Path) -> dict[str, Path]:
    """Discover all .sql files under *concepts_dir*, excluding concept_map/.

    Returns ``{stem: relative_path}`` (stems are lowercased).
    Raises ``ValueError`` on duplicate stems.
    """
    concepts_dir = concepts_dir.resolve()
    stems: dict[str, Path] = {}
    duplicates: list[str] = []

    for sql_file in sorted(concepts_dir.rglob("*.sql")):
        rel = sql_file.relative_to(concepts_dir)
        if rel.parts and rel.parts[0] == "concept_map":
            continue
        stem = sql_file.stem.lower()
        if stem in stems:
            duplicates.append(stem)
        stems[stem] = rel

    if duplicates:
        dup_list = ", ".join(sorted(set(duplicates)))
        raise ValueError(f"Duplicate concept stems found: {dup_list}")

    return stems


# ---------------------------------------------------------------------------
# DAG construction & validation
# ---------------------------------------------------------------------------

def build_graph(concepts_dir: Path) -> dict[str, Any]:
    """Build the concept dependency graph from all SQL files.

    Returns a dict with keys: ``nodes``, ``edges``, ``raw_tables``,
    ``errors``, ``stem_to_rel``, ``sha256_map``.

    Raises ``ValueError`` on duplicate stems (discovery phase).
    Validation errors are collected in ``errors``.
    """
    stem_to_rel = discover_concept_files(concepts_dir)
    all_stems = set(stem_to_rel.keys())

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, str]] = []
    raw_tables: dict[str, set[str]] = defaultdict(set)
    sha256_map: dict[str, str] = {}
    errors: list[dict[str, str]] = []

    for stem, rel_path in sorted(stem_to_rel.items()):
        file_path = concepts_dir / rel_path
        sql_text = file_path.read_text(encoding="utf-8-sig")
        sha = hashlib.sha256(sql_text.encode()).hexdigest()
        sha256_map[stem] = sha

        derived, raw, ambig = _parse_sql_deps(sql_text)

        nodes[stem] = {
            "stem": stem,
            "path": rel_path.as_posix(),
            "sha256": sha,
        }

        for tbl in raw:
            raw_tables[tbl].add(stem)

        for dep in derived:
            if dep == stem:
                errors.append({
                    "type": "self_edge",
                    "stem": stem,
                    "detail": f"Concept '{stem}' references itself",
                })
                continue
            if dep not in all_stems:
                errors.append({
                    "type": "missing_internal_node",
                    "stem": stem,
                    "detail": f"Concept '{stem}' references "
                              f"'{dep}' which is not a known concept SQL file",
                })
                continue
            edges.append({"consumer": stem, "dependency": dep})

        for msg in ambig:
            errors.append({
                "type": "ambiguous_source",
                "stem": stem,
                "detail": msg,
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "raw_tables": dict(raw_tables),
        "errors": errors,
        "stem_to_rel": stem_to_rel,
        "sha256_map": sha256_map,
    }


# ---------------------------------------------------------------------------
# Kahn topological sort
# ---------------------------------------------------------------------------

def kahn_order(
    nodes: set[str],
    edges: list[dict[str, str]],
) -> tuple[list[str], list[str] | None]:
    """Compute a deterministic Kahn topological order.

    Edge direction: ``{"consumer": A, "dependency": B}`` means A depends on B
    (B must come before A in the build order).

    Returns:
        (order, cycle_nodes).  *cycle_nodes* is ``None`` when acyclic,
        otherwise a list of node names participating in a cycle.
    """
    # Adjacency: dependency → set of consumers (reverse of dependency)
    consumers_of: dict[str, set[str]] = defaultdict(set)
    # In-degree: how many dependencies a node has
    indegree: dict[str, int] = {n: 0 for n in nodes}

    for edge in edges:
        consumer = edge["consumer"]
        dep = edge["dependency"]
        indegree[consumer] += 1
        consumers_of[dep].add(consumer)

    # Deterministic queue: sorted list
    queue = deque(sorted(n for n in nodes if indegree.get(n, 0) == 0))
    order: list[str] = []

    while queue:
        node = queue.popleft()
        order.append(node)
        for consumer in sorted(consumers_of.get(node, set())):
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                queue.append(consumer)
        queue = deque(sorted(queue))

    if len(order) != len(nodes):
        remaining = sorted(nodes - set(order))
        return order, remaining

    return order, None


def compute_levels(
    order: list[str],
    edges: list[dict[str, str]],
) -> dict[str, int]:
    """Compute the level of each node (longest-path distance from source).

    Level 0 = no derived dependencies (leaf concepts).
    """
    # adj: consumer → set of its dependencies
    deps_of: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        deps_of[edge["consumer"]].add(edge["dependency"])

    levels: dict[str, int] = {}
    for node in order:
        if not deps_of.get(node):
            levels[node] = 0
        else:
            levels[node] = 1 + max(levels.get(d, 0) for d in deps_of[node])

    return levels


# ---------------------------------------------------------------------------
# DAG dict builder (no I/O — used by both generate and check)
# ---------------------------------------------------------------------------

def _build_dag_dict(concepts_dir: Path) -> dict[str, Any]:
    """Build the full DAG dict in memory without touching disk."""
    concepts_dir = concepts_dir.resolve()
    graph = build_graph(concepts_dir)
    nodes = graph["nodes"]
    edges = graph["edges"]
    all_stems = set(nodes.keys())

    # --- Fail on validation errors ---
    if graph["errors"]:
        details = "\n".join(
            f"  [{e['type']}] {e['stem']}: {e['detail']}"
            for e in graph["errors"]
        )
        raise ValueError(
            f"Concept DAG validation errors — refusing to generate:\n{details}"
        )

    # --- Topological order ---
    order, cycle_nodes = kahn_order(all_stems, edges)
    if cycle_nodes:
        raise ValueError(
            f"Cycle detected in concept DAG: {', '.join(cycle_nodes)}"
        )

    levels = compute_levels(order, edges)

    # --- Level → stems mapping ---
    level_map: dict[int, list[str]] = defaultdict(list)
    for stem, lvl in sorted(levels.items()):
        level_map[lvl].append(stem)

    dag: dict[str, Any] = {
        "generator": "concept_dag",
        "parser_version": PARSER_VERSION,
        "source_root": SOURCE_ROOT_REL,
        "total_concepts": len(nodes),
        "total_edges": len(edges),
        "nodes": {
            stem: {
                **nodes[stem],
                "level": levels.get(stem),
                "dependencies": sorted(
                    {e["dependency"] for e in edges if e["consumer"] == stem}
                ),
                "dependents": sorted(
                    {e["consumer"] for e in edges if e["dependency"] == stem}
                ),
            }
            for stem in sorted(nodes)
        },
        "edges": sorted(edges, key=lambda e: (e["consumer"], e["dependency"])),
        "topological_order": order,
        "levels": {
            str(k): sorted(v) for k, v in sorted(level_map.items())
        },
        "external_tables": {
            tbl: sorted(stems)
            for tbl, stems in sorted(graph["raw_tables"].items())
        },
    }

    return dag


# ---------------------------------------------------------------------------
# Output generation
# ---------------------------------------------------------------------------

def generate_dag(
    concepts_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Generate the concept DAG and write JSON + Markdown artifacts.

    Raises ``ValueError`` on validation errors or cycles (no artifacts are
    written).
    """
    output_dir = output_dir.resolve()

    dag = _build_dag_dict(concepts_dir)

    # Write artifacts
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / _JSON_FILE
    json_path.write_text(json.dumps(dag, indent=2), encoding="utf-8")
    logger.info("Wrote %s", json_path)

    md_path = output_dir / _MD_FILE
    md_path.write_text(_render_markdown(dag), encoding="utf-8")
    logger.info("Wrote %s", md_path)

    return dag


def check_dag(
    concepts_dir: Path,
    output_dir: Path,
) -> bool:
    """Check whether the generated DAG matches the stored artifacts.

    Builds everything in memory — **never overwrites** the on-disk
    artifacts.  Compares both JSON *and* Markdown.

    Returns True if they match, False otherwise.
    """
    json_path = output_dir / _JSON_FILE
    md_path = output_dir / _MD_FILE

    if not json_path.exists() or not md_path.exists():
        logger.error(
            "No stored DAG artifacts at %s — run generate first", output_dir
        )
        return False

    # Build current DAG in memory
    try:
        current_dag = _build_dag_dict(concepts_dir)
    except ValueError as exc:
        logger.error("Current concepts fail validation: %s", exc)
        return False

    current_json = json.dumps(current_dag, indent=2, sort_keys=True)
    current_md = _render_markdown(current_dag)

    stored_json_raw = json_path.read_text(encoding="utf-8")
    stored_md_raw = md_path.read_text(encoding="utf-8")

    # Compare JSON (normalise both via sort_keys)
    try:
        stored_parsed = json.loads(stored_json_raw)
    except json.JSONDecodeError:
        logger.error("Stored JSON is not valid JSON")
        return False
    stored_json_norm = json.dumps(stored_parsed, indent=2, sort_keys=True)

    if current_json != stored_json_norm:
        logger.error("JSON mismatch — DAG has changed")
        return False

    # Compare deterministic Markdown.
    current_md_clean = current_md.strip()
    stored_md_clean = stored_md_raw.strip()

    if current_md_clean != stored_md_clean:
        logger.error("Markdown mismatch — DAG has changed")
        return False

    logger.info("DAG matches stored artifacts (JSON + Markdown).")
    return True


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _safe_mermaid_id(name: str) -> str:
    """Convert a concept stem to a safe Mermaid node ID."""
    return name.replace("-", "_").replace(".", "_")


def _render_markdown(dag: dict[str, Any]) -> str:
    """Render the DAG as a human-readable Markdown document."""
    lines: list[str] = []
    a = lines.append

    a("# Concept DAG")
    a("")
    a(f"**Parser:** {dag['parser_version']}")
    a(f"**Source root:** {dag['source_root']}")
    a(f"**Total concepts:** {dag['total_concepts']}")
    a(f"**Total edges:** {dag['total_edges']}")
    a("")

    # --- Ready Status ---
    levels = dag.get("levels", {})
    a("## Ready / Status")
    a("")
    a("Concepts are organised by build level. Level 0 concepts have no "
      "`mimiciv_derived` dependencies and are statically ready. Higher levels "
      "become ready when each concept's listed dependencies are completed. "
      "Run `mimic_utils status` for live conversion readiness.")
    a("")
    a("| Level | Concepts | Ready? |")
    a("|-------|----------|--------|")
    for lvl_str in sorted(levels.keys(), key=int):
        lvl = int(lvl_str)
        count = len(levels[lvl_str])
        ready = "READY" if lvl == 0 else "after listed dependencies"
        a(f"| {lvl} | {count} | {ready} |")
    a("")

    # --- Build Levels ---
    a("## Build Levels")
    a("")
    for lvl_str in sorted(levels.keys(), key=int):
        lvl = int(lvl_str)
        stems = levels[lvl_str]
        a(f"### Level {lvl} ({len(stems)} concepts)")
        a("")
        if lvl == 0:
            a("| Concept | Path |")
            a("|---------|------|")
            for stem in stems:
                node = dag["nodes"].get(stem, {})
                a(f"| `{stem}` | `{node.get('path', '?')}` |")
        else:
            a("| Concept | Path | Dependencies |")
            a("|---------|------|-------------|")
            for stem in stems:
                node = dag["nodes"].get(stem, {})
                deps = node.get("dependencies", [])
                deps_str = ", ".join(f"`{d}`" for d in deps) if deps else "—"
                a(f"| `{stem}` | `{node.get('path', '?')}` | {deps_str} |")
        a("")

    # --- Topological order ---
    a("## Topological Build Order")
    a("")
    order = dag.get("topological_order", [])
    if order:
        for i, stem in enumerate(order, 1):
            lvl = dag["nodes"].get(stem, {}).get("level", "?")
            a(f"{i}. `{stem}` (level {lvl})")
    a("")

    # --- External tables ---
    a("## External Raw Tables")
    a("")
    ext = dag.get("external_tables", {})
    if ext:
        a("| Table | Schema | Referenced By |")
        a("|-------|--------|--------------|")
        for tbl, refs in sorted(ext.items()):
            schema, _, name = tbl.partition(".")
            refs_str = ", ".join(f"`{r}`" for r in refs)
            a(f"| `{name}` | `{schema}` | {refs_str} |")
    else:
        a("*None*")
    a("")

    # --- Mermaid diagram ---
    a("## Dependency Graph")
    a("")
    a("*Arrow direction: consumer → dependency (A depends on B).*")
    a("")
    a("```mermaid")
    a("graph TD")
    for edge in dag.get("edges", []):
        consumer = _safe_mermaid_id(edge["consumer"])
        dep = _safe_mermaid_id(edge["dependency"])
        a(f"  {consumer} --> {dep}")
    a("```")
    a("")

    # --- All nodes table ---
    a("## All Concepts")
    a("")
    a("| Concept | Path | SHA256 | Level | Deps |")
    a("|---------|------|--------|-------|------|")
    for stem in sorted(dag["nodes"]):
        node = dag["nodes"][stem]
        sha_short = node.get("sha256", "")[:12]
        lvl = node.get("level", "?")
        deps_count = len(node.get("dependencies", []))
        a(f"| `{stem}` | `{node.get('path', '?')}` "
          f"| `{sha_short}` | {lvl} | {deps_count} |")
    a("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API for CLI
# ---------------------------------------------------------------------------

def _resolve_concepts_and_output(
    concepts_dir: str | Path | None,
    output_dir: str | Path | None,
) -> tuple[Path, Path]:
    """Resolve concepts and output directories from CLI args."""
    repo_root = Path(__file__).resolve().parent.parent.parent
    if not concepts_dir:
        cd = repo_root / "mimic-iv" / "concepts"
    else:
        cd = Path(concepts_dir)
    if not output_dir:
        od = cd.parent / _DAG_DIR_NAME if cd.name == "concepts" else cd / _DAG_DIR_NAME
    else:
        od = Path(output_dir)
    return cd, od


def concept_dag_generate(
    concepts_dir: str | Path = "",
    output_dir: str | Path = "",
) -> None:
    """CLI entry point: generate concept DAG artifacts.

    Raises ``ValueError`` if the DAG has validation errors or cycles.
    """
    cd, od = _resolve_concepts_and_output(concepts_dir, output_dir)
    generate_dag(cd, od)


def concept_dag_check(
    concepts_dir: str | Path = "",
    output_dir: str | Path = "",
) -> bool:
    """CLI entry point: check DAG against stored artifact.

    Never overwrites artifacts. Returns True if matching.
    """
    cd, od = _resolve_concepts_and_output(concepts_dir, output_dir)
    return check_dag(cd, od)
