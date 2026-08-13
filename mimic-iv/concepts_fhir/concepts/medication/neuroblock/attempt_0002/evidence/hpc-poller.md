Evidence block:

Concept: neuroblock
Attempt: 0002

Slurm job 29908773 completed normally in 28 seconds. The embedded Pathling/Spark full run executed and fetched `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.

Comparator verdict: `review`, tier `contested`; both `judge_required` and `diagnostician_required` are true. Schema matched exactly. Candidate and oracle each had 14,174 rows, but because declared-unrepresentable `orderid` is the manifest key, the keyed diff is marked VOID DIFF: 14,174 `only_candidate`, 14,174 `only_oracle`, 0 identical, 0 conflicts, and 0 differing-null-only. The counts are not fidelity evidence. The artifact requires an upstream ETL citation and judge review.

Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`; the full candidate remains on scratch.
