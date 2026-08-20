## Demo shape gate — concept `rrt`, attempt 0004

**Verdict: `shape_ok`**

**Execution:** The command `uv run mimic_utils run-demo rrt` executed cleanly via embedded Pathling on Spark against the local demo Delta warehouse. It registered four derived temp views (`rrt_encounter`, `rrt_medication_administration`, `rrt_observation`, `rrt_procedure`), ran `concept.sql`, wrote the candidate Parquet, and ran the shape gate. Exit code 0; overall line was "MAY PROCEED TO FULL DATA".

**Column names:** Candidate returned 7 columns: `stay_id`, `charttime`, `dialysis_present`, `dialysis_active`, `dialysis_type`, `icu_encounter_key`, `patient_key`. The five manifest comparison columns are all present; the two extra columns are the manifest-declared `key_columns` and were accepted as required keys.

**Column types:** Compatible. `shape.demo.json` reports `incompatible_types: []`; Spark/Parquet types (`int`, `timestamp_ntz`, `string`) normalize-compatible with manifest types (`INTEGER`, `TIMESTAMP`, `VARCHAR`).

**Row count (observation, not gated):** 5,130 demo rows versus full-oracle 2,827,715.

**Artifacts:**
- `mimic-iv/concepts_fhir/concepts/treatment/rrt/attempt_0004/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/treatment/rrt/attempt_0004/shape.demo.json`

No execution errors, missing columns, or incompatible types were reported. The demo pass only permits the full-data run; it is not correctness evidence.
