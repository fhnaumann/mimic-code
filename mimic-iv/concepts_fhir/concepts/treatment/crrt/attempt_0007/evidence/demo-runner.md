Evidence block

Concept: `crrt`; attempt: `0007`.

`uv run mimic_utils run-demo crrt` completed successfully through embedded
Pathling on Spark. Verdict: `shape_ok` / `SHAPE OK`.

All 24 oracle columns are present; no columns are missing. The two additional
columns, `icu_encounter_key` and `patient_key`, are the manifest-declared
resource key columns and were not flagged as unexpected. All candidate types
were compatible with the manifest (`INTEGER`, `TIMESTAMP`, `FLOAT`, `VARCHAR`).
The candidate produced 579 demo rows; row count was reported only and was not a
gate. No execution errors occurred. A second invocation was refused because
`candidate.demo.parquet` is write-once; this was an immutability refusal, not a
shape failure.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/shape.demo.json`
