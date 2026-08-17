# Evidence: hpc-poller

HPC job `30057801` completed cleanly (`Slurm COMPLETED`; poll outcome `complete`) and fetched fresh full artifacts. The comparator returned `review`, not a crash or mismatch. Schema matched. Oracle and candidate each had 117,898 rows; row count was informational. A keyed join on `specimen_id` found 117,897 identical rows and one `differing_conflict` on `charttime`; there were no `only_oracle`, `only_candidate`, or `differing_null_only` rows. The divergence tier was `attributed`, with `diagnostician_required: false` and `judge_required: true`. The one conflict was `specimen_id=20137346`, oracle `2150-03-08 02:07`, candidate `03:07`, fully replayed as the `America/New_York` upstream TIMESTAMPTZ DST-gap shift with zero residual. The judge must confirm provenance and that 1/117,898 is consistent with DST-gap rarity.

Artifacts fetched:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
