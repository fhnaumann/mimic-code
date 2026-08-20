# HPC poll evidence — norepinephrine attempt_0002

The controller polled only Slurm job `30232516` from this attempt and fetched
the verdict artifacts. The job outcome was `complete`, with no fatal markers;
Slurm accounting reports 28 seconds elapsed.

The full comparator verdict was `review`, tier `contested`, with both
`divergence.diagnostician_required` and `divergence.judge_required` true. The
candidate executed with schema identity and 336,000 rows, equal to the oracle.
The keyed diff reported 336,000 `only_oracle` and 336,000 `only_candidate`
rows, zero identical rows, and a VOID DIFF note: declared-unrepresentable
`linkorderid` is part of the manifest key `(linkorderid, starttime)`, so keyed
counts do not measure candidate fidelity. Key DST attribution was attempted
but incomplete and did not change the tier.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in this attempt directory. This review must go through
the diagnostician and then the equivalence judge; it is not a match or a
mechanical mismatch.
