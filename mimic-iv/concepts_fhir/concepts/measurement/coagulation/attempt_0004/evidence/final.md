Final evidence — coagulation

- Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the equivalence judge.
- Converged attempt: `attempt_0004`.
- Full-data runs consumed: **3** (attempts 0002, 0003, and 0004). Attempt 0001 failed the demo execution gate and consumed no HPC run.
- Final full verdict: `review`, tier `contested`, accepted as intrinsic upstream transformation loss.
- Full schema: exact ten-column identity. Row counts: candidate/oracle 1,543,003/1,543,003; row count was reported, not gated.
- Keyed diff on `specimen_id`: 1,542,888 identical (99.9925%); 115 `differing_conflict` rows (0.0075%), all on `charttime`; zero `only_oracle`, `only_candidate`, or `differing_null_only` rows.
- Judge citation: `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` casts charttime through TIMESTAMPTZ and writes it to Observation.effectiveDateTime; nonexistent spring-forward 02:xx values become 03:xx in a many-to-one, unrecoverable transformation. `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` repeats the loss and cannot recover the filtered source time. Attempt_0004 uses direct TIMESTAMP_NTZ parsing/output and all other columns are exact.
- Attempt artifacts: `ViewDefinition.lab_observation.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, `ViewDefinition.specimen.json`, `concept.sql`, `candidate.demo.parquet`, `shape.demo.json`, `submit.slurm`, `hpc_job.json`, `comparison.full.json`, and `run_meta.full.json` under the attempt directory.
- Dataset-wide entries appended to `MIMIC_NOTES.d/coagulation.md`: comparator-synthesized Quantity safeguard; datetime choice variants must be cast before COALESCE; outer TIMESTAMP cast reintroduces timezone conversion; lab DST-gap charttimes are irreversibly normalized before FHIR serialization.
- No carryover stage was invalidated. No curated `MIMIC_NOTES.md` file was modified.
