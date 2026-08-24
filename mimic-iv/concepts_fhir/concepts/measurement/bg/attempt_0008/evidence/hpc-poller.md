# HPC poll and full comparison evidence

Concept: `bg`  
Attempt: `attempt_0008`  
Job: `30483911`

The full-data job completed successfully (`slurm_sacct` state `COMPLETED`,
elapsed 574 seconds). The fetched comparator artifact reports `verdict:
match`, schema compatibility, and 511,637 candidate rows versus 511,637 oracle
rows. All 511,637 rows are identical under the comparator tolerances. The
comparator recorded a four-row paired residual involving only float-precision
substitutions in `fio2_chartevents` and `pao2fio2ratio`; it classified these as
equal within tolerance, with zero `differing`, `differing_conflict`,
`differing_null_only`, `only_candidate`, or `only_oracle` rows. There is no
divergence tier and no judge or diagnostician is required.

Produced artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

The candidate full Parquet remains on scratch as specified by the contract.
