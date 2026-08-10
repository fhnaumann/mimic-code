# HPC poller evidence

The submitted job `29603727` was externally cancelled while pending. `sacct` reported `CANCELLED+`, `ExitCode 0:0`, elapsed `00:00:00`, and no start time; `squeue` no longer listed it. No Slurm output, `comparison.full.json`, `run_meta.full.json`, or `candidate.full.parquet` was produced or fetched.

Queue outcome: `crash` due to cancellation before execution. Comparison verdict: none; this is not a `match`, `mismatch`, or `review`. Completed full-data runs: 0. No divergence classes exist and no judge route is applicable. The implementation and `MIMIC_NOTES.md` were unchanged. A new immutable attempt is required for another full run.
