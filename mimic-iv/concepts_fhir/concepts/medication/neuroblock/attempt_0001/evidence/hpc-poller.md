# HPC-poller evidence — neuroblock

Polled Slurm job `29887633` and fetched the full-data artifacts. The job
completed successfully (27 seconds; embedded execution 24.473 seconds,
comparison 0.85 seconds). The schema matched exactly and both oracle and
candidate had 14,174 rows, but row count is non-gating. The comparator returned
`review`, tier `contested`, with `judge_required=true` and
`diagnostician_required=true`. It reported 14,174 `only_candidate` NULL-key
rows and 28,348 `only_oracle` rows, with a VOID DIFF because declared
unrepresentable `orderid` is the manifest key; these counts carry no fidelity
information. Full artifacts are `comparison.full.json`, `run_meta.full.json`,
and `hpc_accounting.json` in this attempt.
