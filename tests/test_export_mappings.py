"""Tests for the exported bundle's MIMIC identifier strip.

The strip is a textual excision -- the parse tree has no positions, and
regenerating SQL from it would reformat every reviewed file -- so what needs
pinning is not just which columns go, but that everything else survives byte
for byte. Most tests here assert on the whole output string rather than on a
parse of it, because a diff that "still parses" is exactly the failure this
module has to rule out.
"""

from __future__ import annotations

import base64

import pytest

from mimic_utils.conversion_state import StateError
from mimic_utils.export_mappings import (
    SIDECAR_BANNER,
    SQL_CONTENT_TYPE,
    SQL_TEXT_EXTENSION,
    _assert_content_agrees,
    _build_library,
    _stage_concept,
    strip_mimic_ids,
)


def _strip(sql: str, concept: str = "c"):
    return strip_mimic_ids(concept, sql)


class TestPairingRule:
    """Drop an identifier iff the same SELECT projects its paired key."""

    def test_paired_identifier_is_dropped(self):
        result = _strip(
            "SELECT\n"
            "    CAST(p.subject_id_str AS INTEGER) AS subject_id,\n"
            "    p.patient_key\n"
            "FROM patient p\n"
        )
        assert result.dropped == ("subject_id",)
        assert result.sql == "SELECT\n    p.patient_key\nFROM patient p\n"

    def test_unpaired_identifier_is_kept_and_reported(self):
        """`dopamine` ships stay_id and no key; stripping it leaves no identity."""
        sql = "SELECT\n    CAST(e.stay_id_str AS INTEGER) AS stay_id,\n    x\nFROM t e\n"
        result = _strip(sql)
        assert result.dropped == ()
        assert result.unpaired == ("stay_id",)
        assert result.sql == sql

    def test_each_identifier_judged_against_its_own_key(self):
        """A concept can be strippable in one identifier and not another."""
        result = _strip(
            "SELECT\n"
            "    a AS subject_id,\n"
            "    b AS stay_id,\n"
            "    p.patient_key\n"
            "FROM t\n"
        )
        assert result.dropped == ("subject_id",)
        assert result.unpaired == ("stay_id",)

    def test_all_four_pairs_are_recognised(self):
        result = _strip(
            "SELECT a AS subject_id, b AS hadm_id, c AS stay_id, d AS specimen_id, "
            "patient_key, encounter_key, icu_encounter_key, specimen_key FROM t"
        )
        assert result.dropped == ("subject_id", "hadm_id", "stay_id", "specimen_id")

    def test_key_alone_is_left_alone(self):
        sql = "SELECT patient_key, x FROM t"
        assert _strip(sql).sql == sql

    def test_non_identifier_columns_are_never_touched(self):
        """anchor_age and linkorderid are always NULL, and still not our business."""
        sql = (
            "SELECT\n"
            "    CAST(NULL AS SMALLINT) AS anchor_age,\n"
            "    CAST(NULL AS INTEGER) AS linkorderid,\n"
            "    patient_key\n"
            "FROM t\n"
        )
        assert _strip(sql).sql == sql


class TestCommaSurgery:
    """Which comma goes with which column, at both ends of the list."""

    def test_first_column_dropped(self):
        """`dobutamine`'s shape: stay_id leads the projection."""
        result = _strip(
            "SELECT\n"
            "    CAST(stay_id_str AS INTEGER) AS stay_id,\n"
            "    CAST(rate_value AS FLOAT) AS vaso_rate,\n"
            "    icu_encounter_key\n"
            "FROM t\n"
        )
        assert result.sql == (
            "SELECT\n"
            "    CAST(rate_value AS FLOAT) AS vaso_rate,\n"
            "    icu_encounter_key\n"
            "FROM t\n"
        )

    def test_last_column_dropped_removes_the_preceding_comma(self):
        result = _strip(
            "SELECT\n"
            "    patient_key,\n"
            "    CAST(p.subject_id_str AS INTEGER) AS subject_id\n"
            "FROM t\n"
        )
        assert result.sql == "SELECT\n    patient_key\nFROM t\n"

    def test_middle_columns_dropped(self):
        result = _strip(
            "SELECT a, b AS subject_id, c, d AS hadm_id, e, patient_key, encounter_key FROM t"
        )
        assert result.sql == "SELECT a, c, e, patient_key, encounter_key FROM t"

    def test_sole_surviving_column_keeps_the_trailing_layout(self):
        result = _strip("SELECT\n    x AS subject_id,\n    patient_key\n\nFROM t\n")
        assert result.sql == "SELECT\n    patient_key\n\nFROM t\n"


class TestFormattingIsPreserved:
    def test_multi_line_projection_item_survives_intact(self):
        """`age`'s wrapped CAST -- the item a naive line-based scan would split."""
        sql = (
            "SELECT\n"
            "    CAST(p.subject_id_str AS INTEGER) AS subject_id,\n"
            "    CAST(\n"
            "        YEAR(TRY_CAST(e.period_start AS TIMESTAMP_NTZ))\n"
            "        - YEAR(TRY_CAST(p.birth_date AS DATE))\n"
            "        AS BIGINT\n"
            "    ) AS age,\n"
            "    p.patient_key\n"
            "FROM t\n"
        )
        result = _strip(sql)
        assert result.dropped == ("subject_id",)
        assert result.sql == (
            "SELECT\n"
            "    CAST(\n"
            "        YEAR(TRY_CAST(e.period_start AS TIMESTAMP_NTZ))\n"
            "        - YEAR(TRY_CAST(p.birth_date AS DATE))\n"
            "        AS BIGINT\n"
            "    ) AS age,\n"
            "    p.patient_key\n"
            "FROM t\n"
        )

    def test_a_multi_line_item_can_itself_be_dropped(self):
        result = _strip(
            "SELECT\n"
            "    CAST(\n"
            "        p.subject_id_str\n"
            "        AS INTEGER\n"
            "    ) AS subject_id,\n"
            "    p.patient_key\n"
            "FROM t\n"
        )
        assert result.sql == "SELECT\n    p.patient_key\nFROM t\n"

    def test_everything_outside_the_projection_is_byte_identical(self):
        sql = (
            "-- leading comment\n"
            "WITH icu AS (\n"
            "    SELECT stay_id_str, subject_id, hadm_id  -- inner ids stay\n"
            "    FROM encounter\n"
            "    WHERE stay_id_str IS NOT NULL\n"
            "),\n"
            "other AS (SELECT 1 AS x)\n"
            "SELECT\n"
            "    CAST(i.subject_id AS INTEGER) AS subject_id,\n"
            "    i.patient_key\n"
            "FROM icu i\n"
            "INNER JOIN other o\n"
            "    ON i.x = o.x  /* block comment, with a comma */\n"
            "WHERE i.hadm_id_str IS NOT NULL\n"
            ";\n"
        )
        result = _strip(sql)
        head, _, tail = sql.partition(
            "    CAST(i.subject_id AS INTEGER) AS subject_id,\n"
        )
        assert result.sql == head + tail

    def test_inner_select_identifiers_are_untouched(self):
        """Only the outermost projection is ours; a CTE's ids are load-bearing."""
        sql = (
            "WITH s AS (SELECT subject_id, patient_key FROM t)\n"
            "SELECT s.subject_id, s.patient_key FROM s\n"
        )
        result = _strip(sql)
        assert result.sql == (
            "WITH s AS (SELECT subject_id, patient_key FROM t)\n"
            "SELECT s.patient_key FROM s\n"
        )

    def test_comment_in_the_select_list_is_refused_rather_than_reattached(self):
        """Nothing says which column a comment between two of them describes."""
        with pytest.raises(StateError, match="comment"):
            _strip(
                "SELECT\n"
                "    a AS subject_id, -- the integer\n"
                "    patient_key -- the key\n"
                "FROM t\n"
            )

    def test_a_comment_is_only_a_problem_where_something_is_stripped(self):
        sql = "SELECT\n    a AS stay_id, -- no key, nothing to drop\n    x\nFROM t\n"
        assert _strip(sql).sql == sql

    def test_comments_outside_the_select_list_are_fine(self):
        result = _strip(
            "-- header\n"
            "WITH s AS (SELECT 1 AS x)  -- a cte\n"
            "SELECT\n"
            "    a AS subject_id,\n"
            "    patient_key\n"
            "FROM s  -- the source\n"
        )
        assert result.sql == (
            "-- header\n"
            "WITH s AS (SELECT 1 AS x)  -- a cte\n"
            "SELECT\n"
            "    patient_key\n"
            "FROM s  -- the source\n"
        )


class TestScannerSafety:
    def test_comma_inside_a_string_literal_is_not_a_separator(self):
        sql = (
            "SELECT\n"
            "    CASE WHEN x = 'a,b' THEN y END AS subject_id,\n"
            "    CONCAT('p,q', 'r') AS note,\n"
            "    patient_key\n"
            "FROM t\n"
        )
        result = _strip(sql)
        assert result.dropped == ("subject_id",)
        assert result.sql == (
            "SELECT\n    CONCAT('p,q', 'r') AS note,\n    patient_key\nFROM t\n"
        )

    def test_comma_inside_a_function_call_is_not_a_separator(self):
        result = _strip(
            "SELECT COALESCE(a, b, c) AS subject_id, patient_key FROM t"
        )
        assert result.sql == "SELECT patient_key FROM t"

    def test_cte_separating_commas_are_not_counted(self):
        result = _strip(
            "WITH a AS (SELECT 1 AS x), b AS (SELECT 2 AS y)\n"
            "SELECT a.x AS subject_id, a.patient_key FROM a, b\n"
        )
        assert result.sql == (
            "WITH a AS (SELECT 1 AS x), b AS (SELECT 2 AS y)\n"
            "SELECT a.patient_key FROM a, b\n"
        )

    def test_subquery_in_the_projection_does_not_confuse_the_scan(self):
        result = _strip(
            "SELECT (SELECT MAX(z) FROM u) AS subject_id, patient_key FROM t"
        )
        assert result.sql == "SELECT patient_key FROM t"


class TestRefusals:
    def test_distinct_is_refused(self):
        """Dropping a column from a DISTINCT projection changes the row count."""
        with pytest.raises(StateError, match="DISTINCT"):
            _strip("SELECT DISTINCT a AS subject_id, patient_key FROM t")

    def test_distinct_without_anything_to_strip_is_fine(self):
        sql = "SELECT DISTINCT a AS stay_id, x FROM t"
        assert _strip(sql).sql == sql

    def test_set_operation_is_refused(self):
        with pytest.raises(StateError, match="not a SELECT"):
            _strip(
                "SELECT a AS subject_id, patient_key FROM t "
                "UNION ALL SELECT b AS subject_id, patient_key FROM u"
            )

    def test_set_operation_without_anything_to_strip_is_fine(self):
        """Refuse only where an edit is actually needed, not on sight of a UNION."""
        sql = "SELECT a AS stay_id FROM t UNION ALL SELECT b AS stay_id FROM u"
        result = _strip(sql)
        assert result.sql == sql
        assert result.unpaired == ("stay_id",)

    def test_unparseable_sql_is_refused(self):
        with pytest.raises(StateError, match="cannot parse"):
            _strip("SELECT FROM WHERE ,,,(")

    def test_missing_from_is_refused(self):
        with pytest.raises(StateError, match="no top-level FROM"):
            _strip("SELECT 1 AS subject_id, 'k' AS patient_key")


class TestIdempotence:
    def test_stripping_twice_equals_stripping_once(self):
        once = _strip(
            "SELECT a AS subject_id, b AS hadm_id, patient_key, encounter_key FROM t"
        )
        twice = _strip(once.sql)
        assert twice.sql == once.sql
        assert twice.dropped == ()

    def test_an_unpaired_concept_is_stable(self):
        sql = "SELECT a AS stay_id, x FROM t"
        assert _strip(_strip(sql).sql).sql == sql


class TestLibraryContent:
    """The SQL is written three times; all three have to say the same thing."""

    SQL = "SELECT patient_key FROM t\n"

    def _library(self):
        return _build_library("age", "3", self.SQL, {"t": "urn:t"})

    def test_content_carries_data_and_sql_text(self):
        content = self._library()["content"][0]
        assert content["contentType"] == SQL_CONTENT_TYPE
        assert base64.b64decode(content["data"]).decode("utf-8") == self.SQL
        assert content["extension"] == [
            {"url": SQL_TEXT_EXTENSION, "valueString": self.SQL}
        ]

    def test_agreement_check_passes_on_a_well_formed_bundle(self):
        sidecar = SIDECAR_BANNER.format(concept="age") + self.SQL
        _assert_content_agrees("age", self._library(), sidecar, self.SQL)

    def test_agreement_check_catches_a_stale_base64_blob(self):
        library = self._library()
        library["content"][0]["data"] = base64.b64encode(b"SELECT 1").decode("ascii")
        sidecar = SIDECAR_BANNER.format(concept="age") + self.SQL
        with pytest.raises(StateError, match="content.data"):
            _assert_content_agrees("age", library, sidecar, self.SQL)

    def test_agreement_check_catches_a_stale_sql_text(self):
        library = self._library()
        library["content"][0]["extension"][0]["valueString"] = "SELECT 1"
        sidecar = SIDECAR_BANNER.format(concept="age") + self.SQL
        with pytest.raises(StateError, match="sql-text"):
            _assert_content_agrees("age", library, sidecar, self.SQL)

    def test_agreement_check_catches_a_sidecar_without_its_banner(self):
        with pytest.raises(StateError, match="sidecar"):
            _assert_content_agrees("age", self._library(), self.SQL, self.SQL)


class _Ctrl:
    """The only thing _stage_concept asks a controller for."""

    def __init__(self, dependencies=()):
        self.dag_raw = {"nodes": {"age": {"dependencies": list(dependencies)}}}


class TestStagedBundle:
    def _attempt(self, tmp_path):
        attempt = tmp_path / "attempt_0003"
        attempt.mkdir()
        (attempt / "concept.sql").write_text(
            "SELECT\n"
            "    CAST(p.subject_id_str AS INTEGER) AS subject_id,\n"
            "    p.birth_date,\n"
            "    p.patient_key\n"
            "FROM patient p\n",
            encoding="utf-8",
        )
        (attempt / "ViewDefinition.patient.json").write_text(
            '{"resourceType": "ViewDefinition", "name": "patient", '
            '"select": [{"column": [{"path": "getResourceKey()", "name": "patient_key"}, '
            '{"path": "identifier.value", "name": "subject_id_str"}]}]}',
            encoding="utf-8",
        )
        return attempt

    def test_the_three_copies_agree_on_disk(self, tmp_path):
        out = tmp_path / "out"
        result = _stage_concept(_Ctrl(), "age", self._attempt(tmp_path), out)
        assert result.dropped == ("subject_id",)

        import json

        sidecar = (out / "age.sql").read_text(encoding="utf-8")
        library = json.loads((out / "Library.age.json").read_text(encoding="utf-8"))
        content = library["content"][0]
        decoded = base64.b64decode(content["data"]).decode("utf-8")

        assert decoded == content["extension"][0]["valueString"]
        assert sidecar == SIDECAR_BANNER.format(concept="age") + decoded
        assert "subject_id" not in decoded
        assert "patient_key" in decoded

    def test_sidecar_banner_names_the_authoritative_file(self, tmp_path):
        out = tmp_path / "out"
        _stage_concept(_Ctrl(), "age", self._attempt(tmp_path), out)
        assert "Library.age.json" in (out / "age.sql").read_text(encoding="utf-8")

    def test_viewdefinition_columns_are_left_alone(self, tmp_path):
        """The strip touches SQL only; a now-unread VD column is not pruned."""
        import json

        out = tmp_path / "out"
        _stage_concept(_Ctrl(), "age", self._attempt(tmp_path), out)
        viewdef = json.loads(
            (out / "ViewDefinition.patient.json").read_text(encoding="utf-8")
        )
        names = [c["name"] for c in viewdef["select"][0]["column"]]
        assert names == ["patient_key", "subject_id_str"]
