# HPC poller evidence

Slurm job `29605737` completed and produced fresh full-data artifacts. Queue outcome: `complete`; comparison verdict: `review`, not `mismatch`. This was attempt 0002's first completed full run.

Hard schema gate passed: columns and types match exactly. Candidate and oracle row counts both equal 39,534; row count is non-gating. The unkeyed full-tuple comparison reported `classification: unavailable_no_key`, tier `contested`, with 3,182 `only_candidate` and 3,182 `only_oracle` rows (8.049%); sample candidate-only rows have NULL `starttime`/`stoptime`, while sample oracle-only rows have non-NULL timestamps. No keyed conflict/null class could be separated. The judge requires a diagnostician first because this is a contested review. No judge was called yet.

Artifacts: `comparison.full.json` and `run_meta.full.json` under attempt 0002. Candidate full Parquet remains on scratch per contract. No implementation or shared-note changes were made.
