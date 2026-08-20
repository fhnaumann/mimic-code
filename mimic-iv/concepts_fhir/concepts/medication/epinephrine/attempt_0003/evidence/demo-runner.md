Evidence

Concept: **epinephrine** · Attempt: **attempt_0003** · Verdict: **`shape_ok`** (overall "MAY PROCEED TO FULL DATA").

- **Executed:** Yes — embedded Pathling on Spark over the demo Delta warehouse ran without error. Views registered: `encounter_icu`, `medication_administration`.
- **Column-name comparison:** All 6 manifest columns present (`stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`). Extra `patient_key` and `icu_encounter_key` match the manifest's declared `key_columns` and are expected additive outputs. Missing columns: none.
- **Type comparison:** Compatible — candidate `int`/`float`/`timestamp_ntz` vs manifest `INTEGER`/`FLOAT`/`TIMESTAMP`; `incompatible_types` empty.
- **Row count (observation, non-gating):** 36 candidate demo rows; oracle full row count 24,470.
- **Artifacts:** `mimic-iv/concepts_fhir/concepts/medication/epinephrine/attempt_0003/candidate.demo.parquet` and `shape.demo.json`.
- **Error output:** None; run completed and closed cleanly.

This is a shape-only pass and earns permission to spend an HPC run, not correctness. No implementation artifacts were edited and no commit was made.
