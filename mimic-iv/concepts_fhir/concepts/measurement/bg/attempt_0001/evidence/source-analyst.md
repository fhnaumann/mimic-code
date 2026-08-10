# Source-analyst evidence — bg

**Concept:** `measurement/bg` (blood gases).

**Read:** `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the DAG node and
`external_tables`, `mimic-iv/concepts/measurement/bg.sql`, the full oracle
manifest, relevant v2.2 DDLs, the carryover CLI implementation, and a prior
carryover example.

**Checked:** `bg.sql` SHA256 is
`90a7f58852b5af97cfce799e9e76a9754c765e2fb9593860ca6bf85b60a5cd55`, matching
the DAG; it is level 0 with no dependencies. The manifest target has 511,637
rows and 27 columns. Demo read-only probes confirmed the relevant schemas.

**Findings:** The source pivots 25 hard-coded blood-gas `labevents` itemids by
`specimen_id`, enriches with most-recent ICU SpO2 (220277, within 2 hours) and
FiO2 (223835, within 4 hours), applies `ROW_NUMBER()` selection and plausibility
filters, and keeps rows with non-null `po2`. It outputs 27 columns including
23 numeric pivots, specimen text, charted/lab FiO2, `aado2_calc`, and
`pao2fio2ratio`. Lab FiO2 is preferred over chart FiO2. The output is unkeyed:
the manifest requires full-tuple multiset comparison; demo-derived keys are
unsafe for `bg`. BigQuery `DATETIME_SUB`/numeric casts need Spark translation,
and `fio2_chartevents` must preserve FLOAT while other numeric outputs are
DOUBLE.

**Dataset-wide finding promoted:** MIMIC-IV 2.2 `d_labitems` has no
`loinc_code`; this sharpened the existing proprietary/flat coding entry in
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`. Existing identifier casts,
`TIMESTAMP_NTZ`, lab time joins, and blood-glucose notes were read and not
duplicated.

**Artifacts:**

- `mimic-iv/concepts_fhir/carryover/bg/source-analyst.md`
- `mimic-iv/concepts_fhir/carryover/bg/carryover.json`
- updated `mimic-iv/concepts_fhir/MIMIC_NOTES.md`
