# Final evidence: `bg`

- Concept: `bg` (`measurement/bg`)
- Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the equivalence judge
- Converged attempt: `attempt_0006`
- Full-data runs consumed in this continuation: **2** (`attempt_0005` and `attempt_0006`)
- Full-data verdict: `review`, accepted; not an exact `match`
- Demo: attempt 0006 `shape_ok`; exact 27-column schema and compatible types
- Full schema: exact 27-column match
- Full row counts: candidate 511,637; oracle 511,637; row count not gated
- Divergence: unkeyed full-tuple multiset; 70 `only_candidate` and 70
  `only_oracle` substitutions (0.014% of rows), classification
  `unavailable_no_key`, tier `contested`
- Judge citation: `mimic-fhir/sql/fhir_observation_labevents.sql:15,121`,
  `fhir_observation_chartevents.sql:9,67`, and
  `mimic-fhir/sql/fhir_specimen_lab.sql:18,58` irreversibly normalize DST-gap
  chart times through `TIMESTAMPTZ`; the original wall time is not recoverable
  from FHIR. The separate comments fallback at
  `fhir_observation_labevents.sql:133-136` is handled by the port.

Key artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `shape.demo.json`
- `candidate.demo.parquet/`
- `submit.slurm`
- `hpc_job.json`
- `evidence/` stage blocks for implementer, demo, launcher, poller, and judge

`MIMIC_NOTES.md`: no entry added or updated for this concept.
