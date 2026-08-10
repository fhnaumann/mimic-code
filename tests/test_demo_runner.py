"""Tests for the demo shape gate.

There is one execution path -- embedded Pathling on Spark, writing Parquet --
because that is what the HPC full run does, and a second path would mean the
Spark leg's first real execution happens on the HPC. These tests pin the
artifact contract and the gate semantics from ``LOOP_CONTRACT.md`` that are easy
to regress: row count is not gated, and zero rows is ``unsure``, never ``fail``.

The executor is faked -- there is no JVM here. What is under test is the
dispatch, the artifact writing and the verdict, all of which are this repo's own
logic. The Parquet write is faked too, but faithfully: it writes a real Parquet
part-file through DuckDB, so the shape gate reads a real schema and the
all-null-column case is exercised end to end rather than asserted about.
"""

from __future__ import annotations

import json

import pytest

from mimic_utils.demo_runner import (
    DemoRunError,
    discover_view_definitions,
    run_demo,
)

COLUMNS = ["subject_id", "hadm_id", "age"]
COLUMN_TYPES = {"subject_id": "int", "hadm_id": "int", "age": "bigint"}
ROWS = [
    {"subject_id": 1, "hadm_id": 100, "age": 40},
    {"subject_id": 2, "hadm_id": 200, "age": 52},
]


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


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


@pytest.fixture
def manifest(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(
            {
                "format_version": "1.0",
                "dataset": "full",
                "schema": "mimiciv_derived",
                "concepts": {
                    "age": {
                        "row_count": 4,
                        "columns": [
                            {"name": "subject_id", "type": "INTEGER"},
                            {"name": "hadm_id", "type": "INTEGER"},
                            {"name": "age", "type": "BIGINT"},
                        ],
                        "key": ["hadm_id"],
                        "comparison": "keyed_join",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return path


class _FakeWriter:
    """Stands in for ``DataFrame.write``, producing a real Parquet part-file.

    Faking the write with a stub would make every schema assertion below a
    tautology. Going through DuckDB means the shape gate reads a genuine
    Parquet schema, so a type that cannot survive the artifact format fails
    here the way it would in a real run.
    """

    def __init__(self, frame):
        self._frame = frame
        self._mode = "errorifexists"

    def mode(self, mode):
        self._mode = mode
        return self

    def parquet(self, path):
        import pathlib

        import duckdb

        target = pathlib.Path(path)
        if target.exists() and self._mode == "error":
            raise RuntimeError(f"path already exists: {target}")
        target.mkdir(parents=True, exist_ok=True)

        # Spark leaves a bare directory when it writes an empty DataFrame with
        # no partitions; reproduce that rather than papering over it.
        if not self._frame._rows and self._frame.empty_writes_no_files:
            return

        con = duckdb.connect(":memory:")
        try:
            select = ", ".join(
                f"CAST(NULL AS {self._frame.sql_types[col]}) AS {col}"
                for col in self._frame.columns
            )
            con.execute(f"CREATE TABLE t AS SELECT {select} WHERE 1=0")
            for row in self._frame._rows:
                values = ", ".join(
                    "NULL" if row.get(c) is None else repr(row.get(c))
                    for c in self._frame.columns
                )
                con.execute(f"INSERT INTO t VALUES ({values})")
            con.execute(
                f"COPY t TO '{target / 'part-00000.parquet'}' (FORMAT PARQUET)"
            )
        finally:
            con.close()


class FakeFrame:
    def __init__(
        self,
        rows,
        columns=COLUMNS,
        dtypes=None,
        sql_types=None,
        empty_writes_no_files=False,
    ):
        self._rows = rows
        self.columns = list(columns)
        self.dtypes = dtypes or list(COLUMN_TYPES.items())
        self.sql_types = sql_types or {
            "subject_id": "INTEGER", "hadm_id": "INTEGER", "age": "BIGINT"
        }
        self.empty_writes_no_files = empty_writes_no_files

    @property
    def write(self):
        return _FakeWriter(self)


class _FakeReader:
    """``spark.read.parquet(...).count()`` over what the writer actually wrote."""

    def parquet(self, path):
        return self

    def __init__(self, frame):
        self._frame = frame

    def count(self):
        return len(self._frame._rows)


class _FakeSpark:
    def __init__(self, frame):
        self._frame = frame

    @property
    def read(self):
        return _FakeReader(self._frame)


class FakeEmbeddedExecutor:
    instances: list["FakeEmbeddedExecutor"] = []
    frame_factory = staticmethod(lambda: FakeFrame(ROWS))

    def __init__(self, warehouse, driver_memory=None, holder=None):
        self.warehouse = warehouse
        self.holder = holder
        self.registered: list[str] = []
        self.sql: str | None = None
        self.closed = False
        self.frame = FakeEmbeddedExecutor.frame_factory()
        FakeEmbeddedExecutor.instances.append(self)

    def register_views(self, definitions):
        self.registered = [d["label"] for d in definitions]
        return self.registered

    def run_sql(self, sql):
        self.sql = sql
        return self.frame

    @property
    def spark(self):
        return _FakeSpark(self.frame)

    def close(self):
        self.closed = True


@pytest.fixture
def fake_embedded(monkeypatch, tmp_path):
    from mimic_utils import embedded_runner

    FakeEmbeddedExecutor.instances = []
    FakeEmbeddedExecutor.frame_factory = staticmethod(lambda: FakeFrame(ROWS))
    warehouse = tmp_path / "delta"
    warehouse.mkdir()
    monkeypatch.setattr(embedded_runner, "EmbeddedExecutor", FakeEmbeddedExecutor)
    return warehouse


def _run(attempt, manifest, warehouse, **kwargs):
    return run_demo(
        "age",
        attempt_dir=attempt,
        manifest_path=manifest,
        warehouse=warehouse,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------


class TestExecution:
    def test_registers_views_runs_the_sql_and_writes_parquet(
        self, attempt, manifest, fake_embedded
    ):
        result = _run(attempt, manifest, fake_embedded)

        executor = FakeEmbeddedExecutor.instances[0]
        assert executor.registered == ["patient"]
        assert executor.sql == "SELECT * FROM patient"
        assert result.view_labels == ["patient"]
        assert result.verdict == "shape_ok"
        assert (attempt / "candidate.demo.parquet").is_dir()
        assert list((attempt / "candidate.demo.parquet").glob("*.parquet"))
        assert (attempt / "shape.demo.json").is_file()

    def test_the_spark_session_is_always_closed(
        self, attempt, manifest, fake_embedded
    ):
        _run(attempt, manifest, fake_embedded)
        assert FakeEmbeddedExecutor.instances[0].closed

    def test_a_spark_failure_is_reported_not_raised(
        self, attempt, manifest, fake_embedded, monkeypatch
    ):
        def boom(self, sql):
            raise RuntimeError("AnalysisException: cannot resolve 'anchor_age'")

        monkeypatch.setattr(FakeEmbeddedExecutor, "run_sql", boom)
        result = _run(attempt, manifest, fake_embedded)
        assert result.blocked
        assert "cannot resolve" in result.errors[0]
        assert not (attempt / "candidate.demo.parquet").exists()


# ---------------------------------------------------------------------------
# gate semantics (LOOP_CONTRACT.md)
# ---------------------------------------------------------------------------


class TestGateSemantics:
    def test_zero_rows_is_unsure_never_fail(self, attempt, manifest, fake_embedded):
        """The 100-patient demo cohort legitimately holds nothing for some
        concepts, so an empty result must not block an HPC run."""
        FakeEmbeddedExecutor.frame_factory = staticmethod(lambda: FakeFrame([]))
        result = _run(attempt, manifest, fake_embedded)

        assert result.verdict == "unsure"
        assert not result.blocked
        assert result.may_proceed_to_full

    def test_zero_rows_still_gets_its_columns_checked(
        self, attempt, manifest, fake_embedded
    ):
        """Parquet carries its schema at zero rows, unlike the old NDJSON
        artifact -- so an `unsure` verdict is no longer schema-blind."""
        FakeEmbeddedExecutor.frame_factory = staticmethod(lambda: FakeFrame([]))
        _run(attempt, manifest, fake_embedded)

        shape = json.loads((attempt / "shape.demo.json").read_text())
        assert shape["verdict"] == "unsure"
        assert shape["schema"].get("checked") is not False
        assert shape["schema"]["match"] is True

    def test_zero_rows_with_no_part_files_is_still_unsure(
        self, attempt, manifest, fake_embedded
    ):
        """Spark can leave a bare directory for an empty DataFrame. A candidate
        that carries no schema at all must not read as the wrong columns."""
        FakeEmbeddedExecutor.frame_factory = staticmethod(
            lambda: FakeFrame([], empty_writes_no_files=True)
        )
        result = _run(attempt, manifest, fake_embedded)

        assert result.verdict == "unsure"
        assert not result.blocked

    def test_a_row_count_disagreement_is_not_a_demo_failure(
        self, attempt, manifest, fake_embedded
    ):
        """The manifest says 4 rows; demo returns 2. Not gated."""
        result = _run(attempt, manifest, fake_embedded)
        assert result.row_count == 2
        assert result.verdict == "shape_ok"
        assert result.may_proceed_to_full

    def test_a_wrong_column_name_blocks(self, attempt, manifest, fake_embedded):
        FakeEmbeddedExecutor.frame_factory = staticmethod(
            lambda: FakeFrame(
                [{"subject_id": 1, "hadm_id": 100, "years": 40}],
                columns=["subject_id", "hadm_id", "years"],
                dtypes=[("subject_id", "int"), ("hadm_id", "int"), ("years", "bigint")],
                sql_types={
                    "subject_id": "INTEGER", "hadm_id": "INTEGER", "years": "BIGINT"
                },
            )
        )
        result = _run(attempt, manifest, fake_embedded)
        assert result.verdict == "shape_fail"
        assert result.blocked
        assert not result.may_proceed_to_full

    def test_an_all_null_column_keeps_its_declared_type(
        self, attempt, manifest, fake_embedded
    ):
        """The regression this artifact format exists to prevent.

        A concept whose shape requires a column MIMIC-on-FHIR cannot populate
        emits `CAST(NULL AS ...)`. Serialised to JSON its type is unrecoverable
        and DuckDB infers `JSON`, failing the manifest's expectation for a
        reason that has nothing to do with the port. Parquet carries the type.
        """
        FakeEmbeddedExecutor.frame_factory = staticmethod(
            lambda: FakeFrame(
                [{"subject_id": 1, "hadm_id": 100, "age": None}],
                dtypes=[("subject_id", "int"), ("hadm_id", "int"), ("age", "bigint")],
            )
        )
        result = _run(attempt, manifest, fake_embedded)

        assert result.verdict == "shape_ok", result.schema_diagnostics
        assert not result.schema_diagnostics


# ---------------------------------------------------------------------------
# artifact contract
# ---------------------------------------------------------------------------


class TestArtifacts:
    def test_refuses_to_overwrite_a_previous_run(
        self, attempt, manifest, fake_embedded
    ):
        (attempt / "candidate.demo.parquet").mkdir()
        result = _run(attempt, manifest, fake_embedded)
        assert "write-once" in result.errors[0]

    def test_refuses_to_overwrite_a_previous_shape_gate(
        self, attempt, manifest, fake_embedded
    ):
        (attempt / "shape.demo.json").write_text("{}", encoding="utf-8")
        result = _run(attempt, manifest, fake_embedded)
        assert "write-once" in result.errors[0]

    def test_a_viewdefinition_name_must_match_its_filename(self, tmp_path):
        attempt = tmp_path / "attempt_0001"
        attempt.mkdir()
        (attempt / "ViewDefinition.patient.json").write_text(
            json.dumps({"resourceType": "ViewDefinition", "name": "other"}),
            encoding="utf-8",
        )
        with pytest.raises(DemoRunError, match="does not match"):
            discover_view_definitions(attempt)

    def test_an_attempt_with_no_viewdefinition_is_rejected(self, tmp_path):
        attempt = tmp_path / "attempt_0001"
        attempt.mkdir()
        with pytest.raises(DemoRunError, match="nothing to register"):
            discover_view_definitions(attempt)
