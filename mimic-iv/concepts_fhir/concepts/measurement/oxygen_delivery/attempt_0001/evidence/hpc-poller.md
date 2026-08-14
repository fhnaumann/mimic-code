## Evidence

Polled Slurm job `29911195` for oxygen_delivery. The job completed successfully
in 179 seconds; this was an executed full-data comparison, not a crash.

Full comparison artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

The schema matched all nine columns. Oracle rows: 601,546; candidate rows:
601,543. The comparator returned `review`, tier `contested`, with 31
`only_candidate`, 34 `only_oracle`, and 3 `differing_conflict` rows. The
comparison reports 31 of 34 oracle-only rows re-pairing through upstream
timestamp-shift key attribution, but three residual rows remain; both judge and
diagnostician are required. Row count was reported only, not gated.
