Evidence block — demo-runner

Ran `uv run mimic_utils run-demo first_day_bg` for attempt `0001` using embedded Pathling 9.6.0 on Spark 4.0.2 over the local demo Delta warehouse. The completed `bg` dependency was preprocessed and views `bg`, `icu_encounter`, and `patient` were registered.

Execution succeeded with exit code 0. All 44 candidate column names matched the oracle manifest (`missing_columns: []`, `extra_columns: []`). Types were compatible: IDs INTEGER, `aado2_calc_min/max` DECIMAL(38,4), and other aggregate columns DOUBLE. Demo row count was 140; this is non-gating evidence under the contract (the full oracle has 73,181 rows, and row count is not a demo gate).

Shape verdict: `shape_ok`; permitted to proceed to full data.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_bg/attempt_0001/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/firstday/first_day_bg/attempt_0001/shape.demo.json`

No implementation, notes, carryover, or commit changes were made beyond CLI artifact output.
