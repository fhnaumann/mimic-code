# HPC poller evidence — enzyme attempt 0003

- Slurm job `30105581` completed normally; `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` were fetched.
- Full comparator verdict: `review`, tier `attributed`; `diagnostician_required: false`, `judge_required: true`.
- Keyed on `specimen_id`: 1,639,449 identical of 1,639,514; 65 `differing_conflict` rows on `charttime`; zero `only_oracle`, `only_candidate`, or `differing_null_only`. All 65 were replayed completely as `upstream_timestamptz_dst_shift`, with zero residual.
- Schema matched all 15 manifest columns and required key columns; candidate and oracle row counts were both 1,639,514 (reported, not gated). Slurm elapsed time was 99 seconds.
- The comparator cites the upstream FHIR datetime cast sites and requires the judge to confirm provenance and DST-gap rarity. Artifacts are under `mimic-iv/concepts_fhir/concepts/measurement/enzyme/attempt_0003/`, including `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
