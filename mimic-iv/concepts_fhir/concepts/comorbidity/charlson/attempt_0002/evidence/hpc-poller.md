## HPC Poll Report — `charlson` attempt 0002

- Job `29965199` completed on the first poll; no fatal marker, resubmission, or execution crash.
- Full-data verdict: `review`, divergence tier `contested`.
- `diagnostician_required: true`; `judge_required: true`.
- Divergence: 61 `differing_conflict` rows (0.014% of 431,231 oracle rows), on `age_score` and `charlson_comorbidity_index`; no gap-shaped or attributed classes.
- Identical rows: 431,170/431,231 (99.99%).
- Conflict attribution was not attempted because the concept has no datetime column; DST attribution is inapplicable.
- Slurm elapsed runtime: 30 seconds; state `COMPLETED`.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in the attempt directory.
- The `review` verdict routes to diagnosis and then the equivalence judge; it is not a failed port.
