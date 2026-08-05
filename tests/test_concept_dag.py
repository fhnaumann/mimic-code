"""Tests for the deterministic static concept DAG generator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from mimic_utils.concept_dag import (
    SOURCE_ROOT_REL,
    _build_dag_dict,
    _parse_sql_deps,
    _safe_mermaid_id,
    build_graph,
    check_dag,
    compute_levels,
    discover_concept_files,
    generate_dag,
    kahn_order,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
CONCEPTS_DIR = REPO_ROOT / "mimic-iv" / "concepts"


@pytest.fixture
def tmp_concepts(tmp_path: Path) -> Path:
    """Create a temporary concepts directory with test SQL files."""
    d = tmp_path / "concepts"
    d.mkdir()
    return d


# ---------------------------------------------------------------------------
# Unit tests: SQL parsing via scope traversal
# ---------------------------------------------------------------------------

def test_parse_simple_derived():
    sql = "SELECT * FROM `physionet-data`.mimiciv_derived.sofa"
    derived, raw, ambig = _parse_sql_deps(sql)
    assert derived == {"sofa"}
    assert raw == set()
    assert ambig == []


def test_parse_raw_table():
    sql = "SELECT * FROM `physionet-data`.mimiciv_icu.chartevents"
    derived, raw, ambig = _parse_sql_deps(sql)
    assert derived == set()
    assert raw == {"mimiciv_icu.chartevents"}
    assert ambig == []


def test_parse_cte_reference_excluded():
    sql = "WITH co AS (SELECT 1) SELECT * FROM co"
    derived, raw, ambig = _parse_sql_deps(sql)
    assert derived == set()
    assert raw == set()
    assert ambig == []


def test_parse_mixed_cte_and_physical():
    sql = """
    WITH uo AS (
        SELECT * FROM `physionet-data`.mimiciv_icu.outputevents
    )
    SELECT *
    FROM `physionet-data`.mimiciv_derived.sofa s
    INNER JOIN uo ON s.stay_id = uo.stay_id
    LEFT JOIN `physionet-data`.mimiciv_icu.icustays ie ON s.stay_id = ie.stay_id
    """
    derived, raw, ambig = _parse_sql_deps(sql)
    assert derived == {"sofa"}
    assert raw == {"mimiciv_icu.outputevents", "mimiciv_icu.icustays"}
    assert ambig == []


def test_parse_unqualified_ambiguous():
    sql = "SELECT * FROM mystery_table"
    derived, raw, ambig = _parse_sql_deps(sql)
    assert derived == set()
    assert raw == set()
    assert len(ambig) == 1
    assert "Unqualified physical" in ambig[0]


def test_parse_non_physionet_catalog():
    sql = "SELECT * FROM other_project.mimiciv_derived.sofa"
    derived, raw, ambig = _parse_sql_deps(sql)
    assert derived == set()
    assert raw == set()
    assert len(ambig) >= 1
    assert any("non-standard catalog" in a or "missing catalog" in a for a in ambig)


def test_parse_db_no_catalog():
    sql = "SELECT * FROM mimiciv_derived.sofa"
    derived, raw, ambig = _parse_sql_deps(sql)
    assert derived == set()
    assert raw == set()
    assert len(ambig) >= 1
    assert any("missing catalog" in a for a in ambig)


def test_parse_no_with_clause():
    """A query without WITH clause still works via scope traversal."""
    sql = "SELECT * FROM `physionet-data`.mimiciv_icu.chartevents"
    derived, raw, ambig = _parse_sql_deps(sql)
    assert raw == {"mimiciv_icu.chartevents"}
    assert derived == set()
    assert ambig == []


# ---------------------------------------------------------------------------
# Integration: parse real concept SQL
# ---------------------------------------------------------------------------

def test_parse_real_sofa_deps():
    """Parse the real sofa.sql and verify extracted dependencies."""
    sql_file = CONCEPTS_DIR / "score" / "sofa.sql"
    sql = sql_file.read_text(encoding="utf-8-sig")
    derived, raw, ambig = _parse_sql_deps(sql)

    assert "icustay_hourly" in derived
    assert "vitalsign" in derived
    assert "gcs" in derived
    assert "enzyme" in derived
    assert "chemistry" in derived
    assert "complete_blood_count" in derived
    assert "urine_output_rate" in derived
    assert "epinephrine" in derived
    assert "norepinephrine" in derived
    assert "dopamine" in derived
    assert "dobutamine" in derived
    assert "bg" in derived
    assert "ventilation" in derived

    assert "mimiciv_icu.icustays" in raw
    assert ambig == []


def test_parse_real_vitalsign_deps():
    """vitalsign.sql has no derived deps."""
    sql_file = CONCEPTS_DIR / "measurement" / "vitalsign.sql"
    sql = sql_file.read_text(encoding="utf-8-sig")
    derived, raw, ambig = _parse_sql_deps(sql)

    assert derived == set()
    assert "mimiciv_icu.chartevents" in raw
    assert ambig == []


def test_parse_real_sepsis3_deps():
    """sepsis3.sql depends on sofa and suspicion_of_infection."""
    sql_file = CONCEPTS_DIR / "sepsis" / "sepsis3.sql"
    sql = sql_file.read_text(encoding="utf-8-sig")
    derived, raw, ambig = _parse_sql_deps(sql)

    assert "sofa" in derived
    assert "suspicion_of_infection" in derived
    assert ambig == []


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def test_discover_concept_files(tmp_concepts):
    (tmp_concepts / "score").mkdir()
    (tmp_concepts / "measurement").mkdir()
    (tmp_concepts / "concept_map").mkdir()
    (tmp_concepts / "score" / "sofa.sql").write_text("SELECT 1")
    (tmp_concepts / "measurement" / "vitalsign.sql").write_text("SELECT 2")
    (tmp_concepts / "concept_map" / "mapping.csv").write_text("a,b")

    stems = discover_concept_files(tmp_concepts)
    assert set(stems.keys()) == {"sofa", "vitalsign"}
    assert stems["sofa"].as_posix() == "score/sofa.sql"


def test_discover_duplicate_stems(tmp_concepts):
    (tmp_concepts / "score").mkdir()
    (tmp_concepts / "other").mkdir()
    (tmp_concepts / "score" / "sofa.sql").write_text("SELECT 1")
    (tmp_concepts / "other" / "sofa.sql").write_text("SELECT 2")

    with pytest.raises(ValueError, match="Duplicate concept stems"):
        discover_concept_files(tmp_concepts)


def test_discover_empty(tmp_concepts):
    stems = discover_concept_files(tmp_concepts)
    assert stems == {}


# ---------------------------------------------------------------------------
# Graph building
# ---------------------------------------------------------------------------

def test_build_graph_simple(tmp_concepts):
    (tmp_concepts / "a.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_derived.b"
    )
    (tmp_concepts / "b.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_icu.raw"
    )
    graph = build_graph(tmp_concepts)
    assert graph["errors"] == []
    assert len(graph["nodes"]) == 2
    edges = graph["edges"]
    assert len(edges) == 1
    assert edges[0]["consumer"] == "a"
    assert edges[0]["dependency"] == "b"


def test_build_graph_self_edge(tmp_concepts):
    (tmp_concepts / "a.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_derived.a"
    )
    graph = build_graph(tmp_concepts)
    assert len(graph["errors"]) == 1
    assert graph["errors"][0]["type"] == "self_edge"
    assert graph["edges"] == []


def test_build_graph_missing_internal(tmp_concepts):
    (tmp_concepts / "a.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_derived.nonexistent"
    )
    graph = build_graph(tmp_concepts)
    assert len(graph["errors"]) == 1
    assert graph["errors"][0]["type"] == "missing_internal_node"


def test_build_graph_ambiguous_source(tmp_concepts):
    (tmp_concepts / "a.sql").write_text(
        "SELECT * FROM mystery_table"
    )
    graph = build_graph(tmp_concepts)
    assert len(graph["errors"]) == 1
    assert graph["errors"][0]["type"] == "ambiguous_source"


def test_build_graph_sha256(tmp_concepts):
    content = "SELECT * FROM `physionet-data`.mimiciv_icu.raw"
    (tmp_concepts / "a.sql").write_text(content)
    graph = build_graph(tmp_concepts)
    expected_sha = hashlib.sha256(content.encode()).hexdigest()
    assert graph["sha256_map"]["a"] == expected_sha
    assert graph["nodes"]["a"]["sha256"] == expected_sha


# ---------------------------------------------------------------------------
# Kahn topological sort
# ---------------------------------------------------------------------------

def test_kahn_order_linear():
    nodes = {"a", "b", "c"}
    edges = [
        {"consumer": "a", "dependency": "b"},
        {"consumer": "b", "dependency": "c"},
    ]
    order, cycle = kahn_order(nodes, edges)
    assert cycle is None
    assert order == ["c", "b", "a"]


def test_kahn_order_diamond():
    nodes = {"a", "b", "c", "d"}
    edges = [
        {"consumer": "c", "dependency": "a"},
        {"consumer": "c", "dependency": "b"},
        {"consumer": "d", "dependency": "c"},
    ]
    order, cycle = kahn_order(nodes, edges)
    assert cycle is None
    idx_a = order.index("a")
    idx_b = order.index("b")
    idx_c = order.index("c")
    idx_d = order.index("d")
    assert idx_a < idx_c
    assert idx_b < idx_c
    assert idx_c < idx_d


def test_kahn_order_leaf_only():
    nodes = {"a", "b", "c"}
    edges: list[dict] = []
    order, cycle = kahn_order(nodes, edges)
    assert cycle is None
    assert sorted(order) == ["a", "b", "c"]


def test_kahn_order_deterministic():
    nodes = {"x", "y", "z"}
    edges = [
        {"consumer": "z", "dependency": "x"},
        {"consumer": "z", "dependency": "y"},
    ]
    order1, _ = kahn_order(nodes, edges)
    for _ in range(10):
        order2, _ = kahn_order(nodes, edges)
        assert order1 == order2


def test_kahn_order_cycle():
    nodes = {"a", "b", "c"}
    edges = [
        {"consumer": "a", "dependency": "b"},
        {"consumer": "b", "dependency": "c"},
        {"consumer": "c", "dependency": "a"},
    ]
    order, cycle = kahn_order(nodes, edges)
    assert cycle is not None
    assert set(cycle) == {"a", "b", "c"}


def test_kahn_order_partial_on_cycle():
    nodes = {"a", "b", "c", "d"}
    edges = [
        {"consumer": "a", "dependency": "b"},
        {"consumer": "b", "dependency": "a"},  # cycle
        {"consumer": "c", "dependency": "d"},  # valid
    ]
    order, cycle = kahn_order(nodes, edges)
    assert cycle is not None
    assert "c" in order
    assert "d" in order
    assert order.index("d") < order.index("c")


# ---------------------------------------------------------------------------
# Level computation
# ---------------------------------------------------------------------------

def test_compute_levels_linear():
    order = ["c", "b", "a"]
    edges = [
        {"consumer": "a", "dependency": "b"},
        {"consumer": "b", "dependency": "c"},
    ]
    levels = compute_levels(order, edges)
    assert levels["c"] == 0
    assert levels["b"] == 1
    assert levels["a"] == 2


def test_compute_levels_diamond():
    order = ["a", "b", "c", "d"]
    edges = [
        {"consumer": "c", "dependency": "a"},
        {"consumer": "c", "dependency": "b"},
        {"consumer": "d", "dependency": "c"},
    ]
    levels = compute_levels(order, edges)
    assert levels["a"] == 0
    assert levels["b"] == 0
    assert levels["c"] == 1
    assert levels["d"] == 2


def test_compute_levels_leaf_only():
    order = ["a", "b", "c"]
    edges: list[dict] = []
    levels = compute_levels(order, edges)
    assert levels["a"] == 0
    assert levels["b"] == 0
    assert levels["c"] == 0


# ---------------------------------------------------------------------------
# Mermaid ID safety
# ---------------------------------------------------------------------------

def test_safe_mermaid_id():
    assert _safe_mermaid_id("hello") == "hello"
    assert _safe_mermaid_id("first_day_sofa") == "first_day_sofa"
    assert _safe_mermaid_id("foo-bar") == "foo_bar"
    assert _safe_mermaid_id("a.b") == "a_b"


# ---------------------------------------------------------------------------
# Integration: generate / check against real concepts
# ---------------------------------------------------------------------------

def test_generate_dag_real(tmp_path):
    """Generate the real DAG and verify JSON + MD are written."""
    output_dir = tmp_path / "concept_dag"
    dag = generate_dag(CONCEPTS_DIR, output_dir)

    json_path = output_dir / "concept_dag.json"
    md_path = output_dir / "concept_dag.md"

    assert json_path.exists()
    assert md_path.exists()

    json_data = json.loads(json_path.read_text())
    assert json_data["generator"] == "concept_dag"
    assert "parser_version" in json_data
    assert json_data["source_root"] == SOURCE_ROOT_REL
    assert json_data["total_concepts"] > 0
    # No "valid" field — errors would raise ValueError
    assert "valid" not in json_data
    assert "validation" not in json_data

    order = json_data["topological_order"]
    assert len(order) == json_data["total_concepts"]

    md_text = md_path.read_text()
    assert "# Concept DAG" in md_text
    assert "## Ready / Status" in md_text
    assert "## Build Levels" in md_text
    assert "## Topological Build Order" in md_text
    assert "```mermaid" in md_text


def test_generate_dag_no_self_edges():
    """Verify the real DAG has no self-edges."""
    output_dir = CONCEPTS_DIR.parent / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)

    json_data = json.loads((output_dir / "concept_dag.json").read_text())
    for edge in json_data["edges"]:
        assert edge["consumer"] != edge["dependency"], \
            f"Self-edge: {edge['consumer']} -> {edge['dependency']}"


def test_generate_dag_no_cycles():
    """Verify the real DAG is acyclic."""
    output_dir = CONCEPTS_DIR.parent / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)

    json_data = json.loads((output_dir / "concept_dag.json").read_text())
    # If there were cycles, generate_dag would have raised ValueError
    assert len(json_data["topological_order"]) == json_data["total_concepts"]


def test_generate_dag_all_nodes_have_level():
    output_dir = CONCEPTS_DIR.parent / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)

    json_data = json.loads((output_dir / "concept_dag.json").read_text())
    for stem, node in json_data["nodes"].items():
        assert node["level"] is not None, f"Node '{stem}' has no level"


def test_generate_dag_levels_consistent():
    """If A depends on B, level(A) > level(B)."""
    output_dir = CONCEPTS_DIR.parent / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)

    json_data = json.loads((output_dir / "concept_dag.json").read_text())
    nodes = json_data["nodes"]
    for edge in json_data["edges"]:
        consumer = edge["consumer"]
        dep = edge["dependency"]
        assert nodes[consumer]["level"] > nodes[dep]["level"], (
            f"Level violation: {consumer} (L{nodes[consumer]['level']}) "
            f"depends on {dep} (L{nodes[dep]['level']})"
        )


def test_generate_dag_concepts_exist(tmp_path):
    stems = discover_concept_files(CONCEPTS_DIR)
    output_dir = tmp_path / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)

    json_data = json.loads((output_dir / "concept_dag.json").read_text())
    dag_stems = set(json_data["nodes"].keys())
    discovered = set(stems.keys())
    assert dag_stems == discovered, (
        f"Mismatch: in DAG: {dag_stems - discovered}, "
        f"discovered: {discovered - dag_stems}"
    )


def test_generate_dag_no_generated_at_in_json(tmp_path):
    """JSON artifact must not contain generated_at (machine-independent)."""
    output_dir = tmp_path / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)
    json_data = json.loads((output_dir / "concept_dag.json").read_text())
    assert "generated_at" not in json_data


def test_generate_dag_source_root_is_relative(tmp_path):
    """source_root must be the stable repo-relative path."""
    output_dir = tmp_path / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)
    json_data = json.loads((output_dir / "concept_dag.json").read_text())
    assert json_data["source_root"] == SOURCE_ROOT_REL


def test_check_dag_matches(tmp_path):
    output_dir = tmp_path / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)
    assert check_dag(CONCEPTS_DIR, output_dir) is True


def test_check_dag_not_matches(tmp_path):
    output_dir = tmp_path / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)

    json_path = output_dir / "concept_dag.json"
    data = json.loads(json_path.read_text())
    data["total_concepts"] = 9999
    json_path.write_text(json.dumps(data, indent=2))

    assert check_dag(CONCEPTS_DIR, output_dir) is False


def test_check_dag_no_artifact(tmp_path):
    output_dir = tmp_path / "nonexistent"
    assert check_dag(CONCEPTS_DIR, output_dir) is False


def test_check_dag_does_not_overwrite(tmp_path):
    """check_dag must never write to disk."""
    output_dir = tmp_path / "concept_dag"
    generate_dag(CONCEPTS_DIR, output_dir)

    json_path = output_dir / "concept_dag.json"
    md_path = output_dir / "concept_dag.md"
    orig_json_mtime = json_path.stat().st_mtime
    orig_md_mtime = md_path.stat().st_mtime

    # Even when check fails, files must not be touched
    data = json.loads(json_path.read_text())
    data["total_concepts"] = 0
    json_path.write_text(json.dumps(data, indent=2))

    result = check_dag(CONCEPTS_DIR, output_dir)
    assert result is False
    # JSON was already modified by us, but check_dag must not have rewritten it
    assert json_path.stat().st_mtime != orig_json_mtime  # we changed it
    assert md_path.stat().st_mtime == orig_md_mtime  # untouched


# ---------------------------------------------------------------------------
# Error/corner case tests
# ---------------------------------------------------------------------------

def test_build_dag_dict_fails_on_error(tmp_concepts):
    """Validation errors must raise ValueError (no artifacts written)."""
    (tmp_concepts / "a.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_derived.nonexistent"
    )
    with pytest.raises(ValueError, match="validation errors"):
        _build_dag_dict(tmp_concepts)


def test_generate_dag_fails_on_self_edge(tmp_concepts, tmp_path):
    """generate_dag must raise ValueError, not write an invalid artifact."""
    (tmp_concepts / "a.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_derived.a"
    )
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError, match="validation errors"):
        generate_dag(tmp_concepts, output_dir)
    # No artifacts should exist
    assert not (output_dir / "concept_dag.json").exists()
    assert not (output_dir / "concept_dag.md").exists()


def test_generate_dag_fails_on_cycle(tmp_concepts, tmp_path):
    """generate_dag must raise ValueError on cycles."""
    (tmp_concepts / "a.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_derived.b"
    )
    (tmp_concepts / "b.sql").write_text(
        "SELECT * FROM `physionet-data`.mimiciv_derived.a"
    )
    output_dir = tmp_path / "out"
    with pytest.raises(ValueError, match="[Cc]ycle"):
        generate_dag(tmp_concepts, output_dir)


# ---------------------------------------------------------------------------
# Real SQL files: all parse without error
# ---------------------------------------------------------------------------

def test_all_concept_sql_parse_without_sqlglot_error():
    import sqlglot
    for sql_file in sorted(CONCEPTS_DIR.rglob("*.sql")):
        if "concept_map" in sql_file.parts:
            continue
        sql = sql_file.read_text(encoding="utf-8-sig")
        try:
            sqlglot.parse_one(sql, read="bigquery")
        except Exception as e:
            pytest.fail(
                f"Failed to parse {sql_file.relative_to(CONCEPTS_DIR)}: {e}"
            )


# ---------------------------------------------------------------------------
# Real concepts: verify specific known dependencies
# ---------------------------------------------------------------------------

class TestRealConceptDependencies:
    """Verify specific known relationships in the real concept graph."""

    def test_vitalsign_has_no_derived_deps(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "measurement" / "vitalsign.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert derived == set()

    def test_gcs_has_no_derived_deps(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "measurement" / "gcs.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert derived == set()

    def test_sofa_depends_on_vitalsign(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "score" / "sofa.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert "vitalsign" in derived

    def test_sepsis3_depends_on_sofa(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "sepsis" / "sepsis3.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert "sofa" in derived

    def test_sepsis3_depends_on_suspicion_of_infection(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "sepsis" / "sepsis3.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert "suspicion_of_infection" in derived

    def test_first_day_sofa_depends_on_first_day_vitalsign(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "firstday" / "first_day_sofa.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert "first_day_vitalsign" in derived

    def test_kdigo_stages_depends_on_kdigo_creatinine(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "organfailure" / "kdigo_stages.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert "kdigo_creatinine" in derived

    def test_kdigo_stages_depends_on_kdigo_uo(self):
        derived, _, _ = _parse_sql_deps(
            (CONCEPTS_DIR / "organfailure" / "kdigo_stages.sql")
            .read_text(encoding="utf-8-sig")
        )
        assert "kdigo_uo" in derived
