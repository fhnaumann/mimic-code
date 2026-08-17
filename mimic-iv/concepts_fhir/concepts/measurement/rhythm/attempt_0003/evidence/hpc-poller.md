# HPC full-run evidence

- Concept/attempt: `rhythm`, `0003`; job `30060701`; command `uv run mimic_utils hpc-poll rhythm`.
- Poll outcome: `complete`; Slurm state `COMPLETED`; 3 polls; fresh comparison artifacts fetched.
- Comparator verdict: `review`, tier `attributed`, classification `keyed`.
- Routing: `judge_required=true`, `diagnostician_required=false`; no diagnostician is needed because the comparator replayed the upstream cast over every divergence row with zero residual.
- Divergence: 95 `differing_conflict`, 645 `only_oracle`, and 42 `only_candidate`; 603 only-oracle rows collided onto existing candidate keys. All were attributed to `upstream_timestamptz_dst_shift` and the key replay; identical rows were 5,872,983/5,873,723 (99.9874%). Candidate rows: 5,873,120 versus oracle 5,873,723; row count was reported, not gated.
- Comparator citations include `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` and the other upstream cast sites listed in the comparison artifact. The judge must confirm provenance for the sourced FHIR element, DST-gap rarity, and the aggregation collision implication.
- Slurm elapsed runtime: 374 seconds.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in the attempt directory. No authored artifact or commit was made.
