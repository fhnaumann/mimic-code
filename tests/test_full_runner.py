"""Tests for the full-data correctness run.

Spark and Pathling are substituted (no JVM in CI), but the comparison is not:
these tests build a real DuckDB oracle, write real Parquet part-files the way
Spark does — a *directory* of them — and let the real comparator produce the
verdict. That split is deliberate. The embedded executor is a thin adapter over
somebody else's engine; the parts worth testing are the ones this repo owns:
that a multi-part Spark output is actually readable by the comparator, that the
write-once rule holds, and that a mismatch is reported as a verdict rather than
swallowed as an error.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from mimic_utils.embedded_runner import EmbeddedRunError
from mimic_utils.full_runner import (
    FullRunError,
    format_full_report,
    resolve_oracle,
    run_full,
)

ROWS = [
    (1, 100, 40),
    (2, 200, 52),
    (3, 300, 91),
    (4, 400, 27),
]


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def oracle(tmp_path):
    path = tmp_path / "mimic4-full.db"
    con = duckdb.connect(str(path))
    con.execute("CREATE SCHEMA mimiciv_derived")
    con.execute(
        "CREATE TABLE mimiciv_derived.age "
        "(subject_id INTEGER, hadm_id INTEGER, age BIGINT)"
    )
    values = ", ".join(str(r) for r in ROWS)
    con.execute(f"INSERT INTO mimiciv_derived.age VALUES {values}")
    con.close()
    return path


@pytest.fixture
def manifest(tmp_path, oracle):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "format_version": "1.0",
                "dataset": "full",
                "schema": "mimiciv_derived",
                "oracle": {"path": str(oracle)},
                "concepts": {
                    "age": {
                        "row_count": len(ROWS),
                        "columns": [
                            {"name": "subject_id", "type": "INTEGER"},
                            {"name": "hadm_id", "type": "INTEGER"},
                            {"name": "age", "type": "BIGINT"},
                        ],
                        "key": ["hadm_id"],
                        "comparison": "keyed_join",
                        "content_hash": "abc",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def warehouse(tmp_path):
    path = tmp_path / "spark_warehouse"
    path.mkdir()
    return path


@pytest.fixture
def attempt(tmp_path):
    path = tmp_path / "attempt_0001"
    path.mkdir()
    (path / "concept.sql").write_text("SELECT * FROM patient", encoding="utf-8")
    (path / "ViewDefinition.patient.json").write_text(
        json.dumps({"resourceType": "ViewDefinition", "name": "patient"}),
        encoding="utf-8",
    )
    return path


class FakeWriter:
    def __init__(self, frame):
        self._frame = frame
        self._mode = None

    def mode(self, mode):
        self._mode = mode
        return self

    def parquet(self, path):
        target = Path(path)
        if target.exists() and self._mode == "error":
            raise RuntimeError(f"path already exists: {target}")
        target.mkdir(parents=True)
        # Spark writes a *directory* of part-files, not a single file. Writing
        # two here is what proves the comparator's glob handles the real shape.
        con = duckdb.connect(":memory:")
        try:
            for index, chunk in enumerate(self._frame.chunks):
                if not chunk:
                    continue
                values = ", ".join(str(row) for row in chunk)
                part = target / f"part-{index:05d}.snappy.parquet"
                con.execute(
                    f"COPY (SELECT * FROM (VALUES {values}) "
                    f"AS t({', '.join(self._frame.columns)})) "
                    f"TO '{part}' (FORMAT PARQUET)"
                )
        finally:
            con.close()


class FakeFrame:
    """Enough of a Spark DataFrame for the runner: columns, dtypes, writer."""

    def __init__(self, columns, dtypes, chunks):
        self.columns = list(columns)
        self.dtypes = list(dtypes)
        self.chunks = chunks

    @property
    def write(self):
        return FakeWriter(self)


AGE_DTYPES = [("subject_id", "int"), ("hadm_id", "int"), ("age", "bigint")]


class FakeExecutor:
    """Stands in for embedded Pathling; records what it was asked to run."""

    def __init__(self, frame=None, error=None):
        self.frame = frame
        self.error = error
        self.registered: list[str] = []
        self.sql: str | None = None
        self.closed = False

    def register_views(self, definitions):
        self.registered = [d["label"] for d in definitions]
        return self.registered

    def run_sql(self, sql):
        self.sql = sql
        if self.error:
            raise self.error
        return self.frame

    def close(self):
        self.closed = True


def _frame(chunks):
    return FakeFrame(["subject_id", "hadm_id", "age"], AGE_DTYPES, chunks)


def _run(attempt, warehouse, oracle, manifest, executor):
    return run_full(
        "age",
        attempt_dir=attempt,
        warehouse=warehouse,
        oracle=oracle,
        manifest_path=manifest,
        executor=executor,
    )


# ---------------------------------------------------------------------------
# the happy path
# ---------------------------------------------------------------------------


class TestMatch:
    def test_reports_a_match_and_writes_every_artifact(
        self, attempt, warehouse, oracle, manifest
    ):
        executor = FakeExecutor(_frame([ROWS[:2], ROWS[2:]]))
        result = _run(attempt, warehouse, oracle, manifest, executor)

        assert result.matched
        assert result.verdict == "match"
        assert (attempt / "candidate.full.parquet").is_dir()
        assert (attempt / "comparison.full.json").is_file()
        assert (attempt / "run_meta.full.json").is_file()

    def test_registers_the_views_and_runs_the_concept_sql(
        self, attempt, warehouse, oracle, manifest
    ):
        executor = FakeExecutor(_frame([ROWS]))
        _run(attempt, warehouse, oracle, manifest, executor)

        assert executor.registered == ["patient"]
        assert executor.sql == "SELECT * FROM patient"

    def test_run_meta_records_the_provenance_of_the_verdict(
        self, attempt, warehouse, oracle, manifest
    ):
        _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS])))
        meta = json.loads((attempt / "run_meta.full.json").read_text(encoding="utf-8"))

        assert meta["verdict"] == "match"
        assert meta["engine"] == "pathling-embedded"
        assert meta["row_count"] == len(ROWS)
        assert meta["oracle"] == str(oracle)
        assert meta["warehouse"] == str(warehouse)
        assert meta["view_labels"] == ["patient"]

    def test_an_injected_executor_is_left_open_for_its_owner_to_close(
        self, attempt, warehouse, oracle, manifest
    ):
        executor = FakeExecutor(_frame([ROWS]))
        _run(attempt, warehouse, oracle, manifest, executor)
        assert not executor.closed


# ---------------------------------------------------------------------------
# mismatches are verdicts, not errors
# ---------------------------------------------------------------------------


class TestMismatch:
    def test_a_missing_row_is_reported_as_review_not_failure(
        self, attempt, warehouse, oracle, manifest
    ):
        """Missing rows are the shape of a coverage gap, so the judge decides."""
        result = _run(
            attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS[:3]]))
        )

        assert result.verdict == "review"
        assert not result.matched
        assert result.needs_judge
        assert not result.errors  # a verdict is not a failure
        assert result.row_count == 3
        assert result.oracle_row_count == 4
        assert any("row count" in d for d in result.diagnostics)

    def test_a_wrong_value_names_the_offending_column(
        self, attempt, warehouse, oracle, manifest
    ):
        wrong = [(1, 100, 41), (2, 200, 52), (3, 300, 91), (4, 400, 27)]
        result = _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([wrong])))

        assert result.verdict == "review"
        assert result.divergence["tier"] == "contested"
        assert any("'age'" in d for d in result.diagnostics)

    def test_the_comparison_artifact_records_a_contested_verdict(
        self, attempt, warehouse, oracle, manifest
    ):
        invented = ROWS + [(9, 900, 55)]
        _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([invented])))
        payload = json.loads(
            (attempt / "comparison.full.json").read_text(encoding="utf-8")
        )
        assert payload["verdict"] == "review"
        assert payload["divergence"]["tier"] == "contested"
        assert payload["divergence"]["judge_bar"]
        assert payload["mode"] == "full"


# ---------------------------------------------------------------------------
# failure handling and the write-once rule
# ---------------------------------------------------------------------------


class TestFailures:
    def test_an_execution_failure_is_recorded_not_raised(
        self, attempt, warehouse, oracle, manifest
    ):
        executor = FakeExecutor(error=EmbeddedRunError("concept SQL failed: no table"))
        result = _run(attempt, warehouse, oracle, manifest, executor)

        assert not result.matched
        assert result.verdict is None
        assert "no table" in result.errors[0]
        assert not (attempt / "comparison.full.json").exists()

    def test_refuses_to_rerun_an_attempt_that_already_has_a_verdict(
        self, attempt, warehouse, oracle, manifest
    ):
        (attempt / "comparison.full.json").write_text("{}", encoding="utf-8")
        executor = FakeExecutor(_frame([ROWS]))
        result = _run(attempt, warehouse, oracle, manifest, executor)

        assert "write-once" in result.errors[0]
        assert executor.sql is None  # nothing was executed

    def test_refuses_when_a_candidate_already_exists(
        self, attempt, warehouse, oracle, manifest
    ):
        (attempt / "candidate.full.parquet").mkdir()
        result = _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS])))
        assert "write-once" in result.errors[0]

    def test_a_missing_manifest_is_reported_before_any_execution(
        self, attempt, warehouse, oracle, tmp_path
    ):
        executor = FakeExecutor(_frame([ROWS]))
        result = _run(attempt, warehouse, oracle, tmp_path / "nope.json", executor)

        assert "manifest not found" in result.errors[0]
        assert executor.sql is None

    def test_there_is_no_default_oracle(self, monkeypatch):
        """A demo oracle must never be able to decide a full-data verdict."""
        monkeypatch.delenv("MIMIC_FULL_ORACLE", raising=False)
        with pytest.raises(FullRunError, match="no default"):
            resolve_oracle(None)

    def test_a_missing_oracle_file_is_rejected(self, tmp_path):
        with pytest.raises(FullRunError, match="not found"):
            resolve_oracle(tmp_path / "absent.db")


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


class TestReport:
    def test_a_match_reads_as_a_pass(self, attempt, warehouse, oracle, manifest):
        result = _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS])))
        report = format_full_report(result, color=False)
        assert "MATCH" in report
        assert "Overall: PASS" in report

    def test_a_conflict_surfaces_the_diagnostics_and_the_bar(
        self, attempt, warehouse, oracle, manifest
    ):
        """A conflict reads as a question with a stated bar, not as a failure.

        Reporting it as FAIL is what made the loop stop short of the judge on
        `age`, whose conflicts were upstream ETL loss the port could not undo.
        """
        wrong = [(1, 100, 41), (2, 200, 52), (3, 300, 91), (4, 400, 27)]
        result = _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([wrong])))
        report = format_full_report(result, color=False)
        assert "REVIEW (contested)" in report
        assert "Overall: FAIL" not in report
        assert "Bar for an accept:" in report
        assert "'age'" in report

    def test_a_review_reads_as_neither_pass_nor_fail(
        self, attempt, warehouse, oracle, manifest
    ):
        result = _run(
            attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS[:2]]))
        )
        report = format_full_report(result, color=False)
        assert "REVIEW" in report
        assert "Overall: REVIEW" in report
        assert "PASS" not in report and "FAIL" not in report
        assert "row count" in report


# ---------------------------------------------------------------------------
# declared-unrepresentable columns, picked up from the attempt directory
#
# The HPC leg gets no CLI flag, so `run_full` must find `unrepresentable.json`
# beside `concept.sql` on its own.
# ---------------------------------------------------------------------------


class _TypedNull:
    """Renders as a typed NULL, which is exactly what the contract requires."""

    def __repr__(self) -> str:
        return "CAST(NULL AS BIGINT)"


NULL_AGE_ROWS = [(r[0], r[1], _TypedNull()) for r in ROWS]

_WHY = "No FHIR element carries this; the IG collapses it into Patient.birthDate."


class TestUnrepresentableDeclaration:
    def test_declaration_is_discovered_and_confirmed(
        self, attempt, warehouse, oracle, manifest
    ):
        (attempt / "unrepresentable.json").write_text(
            json.dumps({"age": _WHY}), encoding="utf-8"
        )
        result = _run(
            attempt, warehouse, oracle, manifest,
            FakeExecutor(_frame([NULL_AGE_ROWS])),
        )

        assert result.verdict == "review"
        payload = json.loads(
            (attempt / "comparison.full.json").read_text(encoding="utf-8")
        )
        assert payload["unrepresentable"]["confirmed"] == {"age": _WHY}
        assert payload["unrepresentable"]["violations"] == []

    def test_a_declared_column_holding_values_blocks_the_run(
        self, attempt, warehouse, oracle, manifest
    ):
        (attempt / "unrepresentable.json").write_text(
            json.dumps({"age": _WHY}), encoding="utf-8"
        )
        result = _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS])))

        assert result.verdict == "mismatch"
        payload = json.loads(
            (attempt / "comparison.full.json").read_text(encoding="utf-8")
        )
        assert payload["unrepresentable"]["violations"][0]["column"] == "age"

    def test_absent_declaration_is_not_an_error(
        self, attempt, warehouse, oracle, manifest
    ):
        """Most concepts have none; the file is optional."""
        result = _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS])))
        assert result.verdict == "match"
        payload = json.loads(
            (attempt / "comparison.full.json").read_text(encoding="utf-8")
        )
        assert "unrepresentable" not in payload

    def test_a_malformed_declaration_is_reported_not_ignored(
        self, attempt, warehouse, oracle, manifest
    ):
        (attempt / "unrepresentable.json").write_text(
            json.dumps({"age": "n/a"}), encoding="utf-8"
        )
        result = _run(attempt, warehouse, oracle, manifest, FakeExecutor(_frame([ROWS])))
        assert result.errors and "justification" in result.errors[0]
