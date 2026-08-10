# Demo Shape Gate Evidence: `age` (attempt_0002)

**Stage:** demo-runner (`mimic_utils run-demo age`)
**Date:** 2026-08-07
**Concept:** demographics/age
**Dataset:** demo Delta warehouse (embedded Pathling on Spark)

## Result

**SHAPE OK** — verdict in `attempt_0002/shape.demo.json`.

- Executed: true
- Result columns (6): subject_id int, hadm_id int, admittime timestamp_ntz,
  anchor_age smallint, anchor_year smallint, age bigint
- All six expected column NAMES present, no missing/extra.
- All column TYPES compatible with the manifest (subject_id/hadm_id INTEGER,
  admittime TIMESTAMP, anchor_age/anchor_year SMALLINT, age BIGINT).
- Result rows: 275 (observation — NOT gated; oracle full row count 431,231).

## Interpretation

This is a cheap SHAPE gate only — it confirms the port executes, has the right
column names and types, and that the INTEGER casts fixed the attempt_0001
failure. It is NOT evidence of correctness. 275 rows on the 100-patient demo
cohort vs 431,231 on full data is expected (cohort size). Proceeding to the
full-data correctness gate on HPC.

## MIMIC_NOTES.md entries consulted

Identifier-as-STRING casts, TIMESTAMP_NTZ, hosp Encounter filter, birthDate
year subtraction, typed NULLs. **No new entry added.**
