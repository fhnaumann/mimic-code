# Demo runner — vasoactive_agent attempt_0003

Command: `uv run mimic_utils run-demo vasoactive_agent` (run from repo root)

## Result: shape_ok

Executed successfully (embedded Pathling on Spark over the demo Delta warehouse).
Exit code 0. Gate verdict `shape_ok` (`shape.demo.json` → `match: true`).

## Schema comparison vs. oracle_manifest.full.json

Oracle expected columns (names + types):
- stay_id INTEGER
- starttime TIMESTAMP
- endtime TIMESTAMP
- dopamine FLOAT
- epinephrine FLOAT
- norepinephrine FLOAT
- phenylephrine FLOAT
- vasopressin FLOAT
- dobutamine FLOAT
- milrinone FLOAT

Candidate returned columns (12) and their types:
- stay_id INT, starttime TIMESTAMP_NTZ, endtime TIMESTAMP_NTZ
- dopamine, epinephrine, norepinephrine, phenylephrine, vasopressin, dobutamine, milrinone — all FLOAT
- plus `icu_encounter_key` STRING, `patient_key` STRING

Column names: all 10 oracle columns present, none missing, no unexpected columns.
The two additional columns (`icu_encounter_key`, `patient_key`) are the manifest
`key_columns` for this concept; the gate records them under `required_key_columns`
and `extra_columns`, not `unexpected_columns` (`unexpected_columns: []`,
`missing_key_columns: []`). Types compatible (`incompatible_types: []`).

## Row count (non-gating observation)

Candidate demo rows: 1,874. Oracle full-data row count: 665,529.
Reported as observation only — row count is not a demo gate.

## Artifacts

- `candidate.demo.parquet/` — written under attempt_0003
- `shape.demo.json` — verdict `shape_ok`, `match: true`

No implementation artifacts were edited. No git commit.