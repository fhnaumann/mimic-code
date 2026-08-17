## Demo shape gate — `charlson` attempt 0005

**Command:** `uv run mimic_utils run-demo charlson` (embedded Pathling on Spark over the demo Delta warehouse, `/Users/nau025/warehouses/mimic-iv-demo/delta`)

**Executed:** yes. Spark session started (pathling 9.6.0, delta-spark 4.0.0), views registered (`age`, `condition`, `encounter`, `patient`), ViewDefinitions run, `concept.sql` executed, Parquet written. Exit code `0`.

**Shape gate verdict (from `shape.demo.json`):** `shape_ok` — `executed: true`, `verdict: "shape_ok"`, `schema.match: true`.

**Column names:** All 21 oracle columns present, in order: `subject_id`, `hadm_id`, `age_score`, `myocardial_infarct`, `congestive_heart_failure`, `peripheral_vascular_disease`, `cerebrovascular_disease`, `dementia`, `chronic_pulmonary_disease`, `rheumatic_disease`, `peptic_ulcer_disease`, `mild_liver_disease`, `diabetes_without_cc`, `diabetes_with_cc`, `paraplegia`, `renal_disease`, `malignant_cancer`, `severe_liver_disease`, `metastatic_solid_tumor`, `aids`, `charlson_comorbidity_index`. Missing: none. Extra: `patient_key`, `encounter_key` — exactly the manifest's declared `key_columns`. All expected columns matched; `unexpected_columns: []`.

**Column types:** all expected columns compatible (`int` vs. manifest `INTEGER`); `incompatible_types: []`.

**Row count:** 275 rows returned — observation only, not gated. Since rows > 0, verdict is `shape_ok`, not `unsure`.

**Artifacts produced:**
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/shape.demo.json`

No errors; no files edited and no commit made. Demo pass earns permission for a full-data run only; it is not evidence of correctness.
