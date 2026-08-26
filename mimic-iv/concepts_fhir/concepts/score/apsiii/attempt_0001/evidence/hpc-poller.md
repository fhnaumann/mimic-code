# HPC poller evidence

Concept: `apsiii`, attempt `0001`.

`uv run mimic_utils hpc-poll apsiii` followed the existing write-once job record for Slurm job `30512123`, waited through 8 polls, and completed successfully. The fetched comparator artifact reports schema match, candidate/oracle row counts 73,181/73,181 (reported only), and a `review` verdict at tier `gap_shaped`. The keyed diff on `stay_id` has 62,892 identical rows and 10,289 `differing_null_only` rows, all on `gcs_score`; there are no `only_oracle`, `only_candidate`, or `differing_conflict` rows. The candidate is NULL where the oracle has a value, matching the missing served GCS discriminator shape. `diagnostician_required` is false and `judge_required` is true, so the next stage is the equivalence judge without a diagnostician.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/score/apsiii/attempt_0001/`. Slurm elapsed time was reported as 1997 seconds. No semantic decision was made by the poller.
