# HPC-poller evidence — neuroblock attempt 0005

Job `30235056` completed on Slurm and fetched a fresh full-data comparison.
The comparator returned `review`, with schema execution and shape valid:
14,174 oracle rows and 14,174 candidate rows, but zero aligned rows because
the manifest key is the declared-unrepresentable `orderid`. It reports
14,174 `only_oracle` and 14,174 `only_candidate` rows and explicitly marks
the diff `VOID DIFF`; these counts are not fidelity evidence. Routing fields
are `tier: contested`, `judge_required: true`, and
`diagnostician_required: true`.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in this attempt directory. Slurm elapsed time was 29
seconds. No second job was launched.
