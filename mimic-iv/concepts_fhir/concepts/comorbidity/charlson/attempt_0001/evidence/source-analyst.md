# Source-analyst evidence — charlson attempt 0001

The source analyst read the DAG, `mimic-iv/concepts/comorbidity/charlson.sql`,
the `age` dependency SQL and carryover, the oracle manifest, `LOOP_CONTRACT.md`,
`MIMIC_NOTES.md`, and relevant notes fragments. Charlson is one row per
hospital admission (`hadm_id`), with 17 ICD-9/ICD-10 prefix/range flags,
age-score thresholds inherited from `mimiciv_derived.age`, and a weighted
Charlson index. It uses admissions as the driving table, left joins grouped
diagnoses and age, and has no WHERE/time filter. All manifest output columns are
INTEGER; `hadm_id` is the natural key. The reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/charlson/source-analyst.md` and registered by
the agent. No UUID or resource-id inversion was proposed.

Artifact: `mimic-iv/concepts_fhir/carryover/charlson/source-analyst.md`.
