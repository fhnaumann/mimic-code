## Evidence

Slurm job `29944812` completed cleanly and the fetched full comparison is a
`review`, not a crash. Schema identity passed for all five columns. The oracle
has 2,827,715 rows and the candidate 2,827,135; row count is non-gating.

The unkeyed comparison reports `classification: unavailable_no_key`,
`tier: contested`, 821 `only_oracle` rows and 241 `only_candidate` rows, with
no attributed or unresolvable conflicts. Both judge and diagnostician are
required. The judge has less evidence because full-tuple multiset comparison
cannot pair residual rows.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in attempt 0001.
