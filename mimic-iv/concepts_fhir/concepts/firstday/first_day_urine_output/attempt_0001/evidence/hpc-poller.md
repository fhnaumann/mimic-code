## HPC poller evidence

Job `30306604` completed successfully and fetched `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`. The comparator returned `review`, tier `contested`, with `diagnostician_required: true` and `judge_required: true`. Schema matched and row counts were equal at 73,181. The keyed diff reproduced 73,171 rows identically and found 10 `differing_conflict` rows, all on `urineoutput`; there were no only-oracle, only-candidate, or differing-null rows. Comparator metadata says DST attribution was not attempted because the final concept has no datetime column. Slurm elapsed time was 144 seconds; execution/compare timings were 140.226/1.198 seconds.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in attempt 0001; `candidate.full.parquet` remains on scratch. This is a review, not a terminal state; the required diagnostician must investigate the ten value conflicts before the judge.
