# Demo runner evidence — antibiotic, attempt_0002

Date: 2026-08-11
Command: `uv run mimic_utils run-demo antibiotic` (embedded Pathling on Spark over the local demo Delta warehouse)

## Outcome

- **Executed:** yes. Views registered: `encounter`, `encounter_icu`, `medication`, `medication_mix`, `medication_request`, `patient`. No execution error.
- **Verdict (shape.demo.json):** `shape_ok` — "Shape is correct. This earns permission to spend an HPC run; it is not evidence of correctness."
- **Exit:** may proceed to full-data validation.

## Shape comparison

Authoritative target from `oracle_manifest.full.json` entry `concepts['antibiotic']` (key: none — `full_tuple_multiset` comparison):

| Column | Oracle type | Candidate type | Compatible |
|---|---|---|---|
| subject_id | INTEGER | int | yes |
| hadm_id | INTEGER | int | yes |
| stay_id | INTEGER | int | yes |
| antibiotic | VARCHAR | string | yes |
| route | VARCHAR | string | yes |
| starttime | TIMESTAMP | timestamp_ntz | yes |
| stoptime | TIMESTAMP | timestamp_ntz | yes |

- Column names: **matching** — no missing, no extra (candidate `actual_columns` identical to `expected_columns`).
- Column types: **compatible** — `incompatible_types: []` in shape.demo.json.

## Row count (observation, NOT a gate)

- Candidate demo rows: **903** (non-zero → verdict `shape_ok`, not `unsure`).
- Oracle full-data row count: 735,462 (informational only).

## Artifacts

- Candidate: `mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0002/candidate.demo.parquet/` (part-00000-e5c0dbc9-72cb-4894-8d52-2e3488236e38-c000.snappy.parquet, `_SUCCESS`)
- Shape gate: `mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0002/shape.demo.json` (format_version 2.0, verdict `shape_ok`)

Demo pass is a shape gate only; correctness is decided on full data.
