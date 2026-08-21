Evidence block

Concept: `first_day_gcs`, attempt 0002.

The submitted job completed with fetched verdict artifacts (`hpc_accounting.json` records job `30315602`, Slurm state COMPLETED, 83 seconds). The authoritative fetched `comparison.full.json` reports `review`, tier `gap_shaped`, with `judge_required: true` and `diagnostician_required: false`.

Schema matched: all seven manifest columns and required opaque key companions were present with compatible types. Candidate and oracle row counts were both 73,181; row count was reported only, not gated. Keyed diff: 72,651 `differing_null_only`, zero `differing_conflict`, zero `only_oracle`, zero `only_candidate`. Candidate NULL counts were `gcs_unable` 72,651 (declared and confirmed), `gcs_min` 28,837, `gcs_eyes` 28,742, `gcs_verbal` 28,651, and `gcs_motor` 28,622. Exact full rows: 530/73,181; identical on representable columns: 44,344/73,181 (60.59%).

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json`, and the existing attempt outputs. This is a legitimate review, not a queue-only result or mismatch; route directly to the equivalence judge and skip the diagnostician. No candidate artifacts were edited and no commit was made.
