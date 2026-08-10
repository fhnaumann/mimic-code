# Terminal evidence: `bg`

The controller state is `COMPLETED_WITH_DIVERGENCE`, accepted by the judge on
attempt 0006. **Total full-data runs consumed for bg: 4** (attempts 0002,
0003, 0005, and 0006); the current continuation consumed the final two.

Attempt 0006 passed execution, exact 27-column schema, and equal 511,637 row
counts. Its unkeyed full-tuple comparison had 70 `only_candidate` and 70
`only_oracle` substitutions (0.014%), accepted as intrinsic DST-gap
normalization after citation of `mimic-fhir/sql/fhir_observation_labevents.sql:15,121`,
`fhir_observation_chartevents.sql:9,67`, and `fhir_specimen_lab.sql:18,58`.
The source/ETL comments fallback at `fhir_observation_labevents.sql:133-136`
was handled by the port.

Comparison artifacts exist for all four consumed full runs under the immutable
attempt directories; the converged artifacts are
`comparison.full.json`, `run_meta.full.json`, `shape.demo.json`, and
`evidence/equivalence-judge.md` in attempt 0006. `MIMIC_NOTES.md` had no entry
added or updated for bg.
