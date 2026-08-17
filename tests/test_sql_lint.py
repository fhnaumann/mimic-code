"""Tests for the deterministic ``concept.sql`` gate.

Each rule here exists because a full-data divergence taught us the class, and
each test pins both directions: the construction is rejected, and the legitimate
construction it is easy to confuse with is not. A rule that fires on correct SQL
blocks the loop, which is the expensive direction of error for a gate no agent
can argue with.
"""

from __future__ import annotations

from mimic_utils.sql_lint import lint_sql_text


def _rules(sql: str) -> set[str]:
    return {finding.rule for finding in lint_sql_text(sql)}


class TestDatetimeRules:
    def test_to_timestamp_is_rejected(self):
        assert "datetime-parser" in _rules(
            "SELECT TO_TIMESTAMP(x, \"yyyy-MM-dd'T'HH:mm:ssXXX\") FROM t"
        )

    def test_try_to_timestamp_is_rejected(self):
        assert "datetime-parser" in _rules("SELECT TRY_TO_TIMESTAMP(x, 'y') FROM t")

    def test_bare_timestamp_cast_is_rejected(self):
        assert "bare-timestamp-cast" in _rules("SELECT CAST(x AS TIMESTAMP) FROM t")

    def test_timestamp_ntz_is_accepted(self):
        assert _rules("SELECT TRY_CAST(x AS TIMESTAMP_NTZ) FROM t") == set()


class TestHardcodedResourceId:
    """`code_status` attempt_0002 shipped nine of these, read off a diff."""

    def test_literal_uuid_is_rejected(self):
        sql = (
            "SELECT CASE observation_key\n"
            "  WHEN 'Observation/1e2075cb-8a2f-5c1a-96cd-f43935684d9c'\n"
            "    THEN CAST('2151-10-03 02:16:00' AS TIMESTAMP_NTZ)\n"
            "  ELSE fhir_charttime END FROM t"
        )
        assert "hardcoded-resource-id" in _rules(sql)

    def test_bare_uuid_without_prefix_is_still_rejected(self):
        # The `Observation/` prefix is incidental; pinning a row by identity is
        # the defect, whatever resource type it names.
        assert "hardcoded-resource-id" in _rules(
            "SELECT * FROM t WHERE k = '0a8eebfd-a352-5c1a-96cd-f43935684d9c'"
        )

    def test_uppercase_uuid_is_rejected(self):
        assert "hardcoded-resource-id" in _rules(
            "SELECT * FROM t WHERE k = '1E2075CB-8A2F-5C1A-96CD-F43935684D9C'"
        )

    def test_commented_out_uuid_is_not_a_violation(self):
        # A rule that fails an attempt for a UUID in a comment is a false
        # rejection, and false rejections block the loop.
        assert _rules(
            "SELECT x FROM t  -- was 'Observation/1e2075cb-8a2f-5c1a-96cd-f43935684d9c'"
        ) == set()

    def test_joining_on_a_resource_key_column_is_accepted(self):
        # Reading an id and joining on it is the correct use; only writing one
        # as a literal is not.
        assert _rules(
            "SELECT o.observation_key FROM obs o JOIN pat p ON o.patient_key = p.patient_key"
        ) == set()


class TestResourceIdInversion:
    """Five concepts recompute the ETL's UUIDv5 to undo a DST shift."""

    def test_uuid_namespace_constant_is_rejected(self):
        assert "resource-id-inversion" in _rules(
            "SELECT UNHEX('36e18860b4aa5577bc80a5b07922cd3d') FROM t"
        )

    def test_hash_call_is_rejected(self):
        assert "resource-id-inversion" in _rules(
            "SELECT SHA1(CONCAT(ns, ENCODE(name, 'UTF-8'))) AS digest FROM t"
        )

    def test_md5_is_rejected(self):
        assert "resource-id-inversion" in _rules("SELECT MD5(name) FROM t")

    def test_uuid_reassembly_shape_is_rejected(self):
        # The full construction from icp/crrt/height/icustay_times: hash, then
        # slice the digest back into 8-4-4-4-12.
        sql = (
            "SELECT CONCAT(\n"
            "  SUBSTR(d.current_digest, 1, 8), '-',\n"
            "  SUBSTR(d.current_digest, 9, 4)\n"
            ") FROM (SELECT SHA1(x) AS current_digest FROM t) d"
        )
        assert "resource-id-inversion" in _rules(sql)

    def test_substr_alone_is_accepted(self):
        # `SUBSTR` is ordinary string work; only hashing marks the inversion.
        assert _rules("SELECT SUBSTR(label, 1, 8) FROM t") == set()

    def test_unhex_of_a_short_literal_is_accepted(self):
        # Only a 32-hex-digit constant is a UUID namespace.
        assert _rules("SELECT UNHEX('ff00') FROM t") == set()


class TestClean:
    def test_an_ordinary_lab_pivot_is_clean(self):
        sql = """
        WITH filtered AS (
            SELECT p.subject_id_str, p.patient_key, s.specimen_id_str, l.code,
                   TRY_CAST(l.effective_datetime AS TIMESTAMP_NTZ) AS charttime,
                   CAST(l.quantity_value AS DOUBLE) AS value_num
            FROM lab_observation l
            INNER JOIN patient p ON l.patient_key = p.patient_key
            LEFT JOIN encounter e ON l.encounter_key = e.encounter_key
            WHERE l.code IN ('51003', '50911')
        )
        SELECT CAST(subject_id_str AS INTEGER) AS subject_id,
               patient_key,
               MAX(CASE WHEN code = '51003' THEN value_num END) AS troponin_t
        FROM filtered GROUP BY subject_id_str, patient_key
        """
        assert lint_sql_text(sql) == []


class TestMissingResourceKey:
    """A MIMIC identifier emitted without the FHIR key it is paired with.

    The defect these guard is not a wrong value but an unusable table: a
    downstream SQL-on-FHIR consumer joins on `getResourceKey()`, so an
    integer-only output joins to nothing -- silently, as zero rows.
    """

    def test_subject_id_without_patient_key_is_flagged(self):
        sql = "SELECT CAST(p.subject_id_str AS INTEGER) AS subject_id FROM patient p"
        assert _rules(sql) == {"missing-resource-key"}

    def test_the_paired_key_clears_it(self):
        sql = (
            "SELECT CAST(p.subject_id_str AS INTEGER) AS subject_id, p.patient_key "
            "FROM patient p"
        )
        assert _rules(sql) == set()

    def test_a_key_joined_on_but_not_emitted_does_not_count(self):
        # The join spine mentions `patient_key` in every port; only the
        # outermost SELECT's output satisfies the rule.
        sql = (
            "SELECT CAST(p.subject_id_str AS INTEGER) AS subject_id "
            "FROM observation o JOIN patient p ON o.patient_key = p.patient_key"
        )
        assert _rules(sql) == {"missing-resource-key"}

    def test_one_finding_per_unpaired_identifier(self):
        sql = (
            "SELECT CAST(p.subject_id_str AS INTEGER) AS subject_id, "
            "CAST(e.hadm_id_str AS INTEGER) AS hadm_id, e.encounter_key "
            "FROM encounter e JOIN patient p ON e.patient_key = p.patient_key"
        )
        findings = [f for f in lint_sql_text(sql) if f.rule == "missing-resource-key"]
        assert [f.message.split()[0] for f in findings] == ["subject_id"]

    def test_patient_key_is_owed_even_without_a_subject_id_column(self):
        # `kdigo_creatinine` emits hadm_id and stay_id and no subject_id. Every
        # concept is patient-scoped, so it owes a patient_key regardless -- and
        # the shape gate requires one, so a lint that let this pass would send a
        # port an hour into a run to learn it.
        sql = (
            "SELECT CAST(e.hadm_id_str AS INTEGER) AS hadm_id, "
            "CAST(i.stay_id_str AS INTEGER) AS stay_id, "
            "e.encounter_key, i.icu_encounter_key "
            "FROM encounter e JOIN icu_encounter i ON 1=1"
        )
        assert _rules(sql) == {"missing-resource-key"}

    def test_a_fragment_emitting_no_identifier_is_not_a_concept_output(self):
        # The unconditional patient_key obligation must not fire on arbitrary
        # SQL; emitting a MIMIC identifier is what marks a concept output.
        assert _rules("SELECT count(*) FROM observation") == set()

    def test_unparseable_sql_yields_no_finding_rather_than_a_false_reject(self):
        # A lint that false-rejects blocks the loop; export_mappings hard-fails
        # on an unparseable file already.
        assert _rules("SELECT AS AS FROM FROM (((") == set()

    def test_findings_carry_line_numbers(self):
        findings = lint_sql_text("SELECT 1\nSELECT MD5(x)\n")
        assert [f.line for f in findings] == [2]
