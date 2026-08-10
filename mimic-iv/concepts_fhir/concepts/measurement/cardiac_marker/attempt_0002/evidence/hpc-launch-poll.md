## HPC launch/poll evidence

`uv run mimic_utils hpc-launch cardiac_marker` staged attempt 2, passed the login-node smoke test, submitted Slurm job `29675600`, and wrote `submit.slurm` and `hpc_job.json`. `uv run mimic_utils hpc-poll cardiac_marker` completed normally and fetched `comparison.full.json` and `run_meta.full.json`.

Full comparator result: `review`, tier `contested`, with schema identity and equal row counts (oracle and candidate 295,246). There are 295,228 identical rows and 18 `differing_conflict` rows, all in `charttime`; each candidate value is one hour ahead of the oracle. No `only_oracle`, `only_candidate`, or gap-shaped class was reported. The comparator requires an upstream ETL citation before any judge acceptance. This was full run 1 for attempt 2 and full run 2 for the concept's hpc counter.

Artifacts: `submit.slurm`, `hpc_job.json`, `comparison.full.json`, and `run_meta.full.json` under `attempt_0002`; the candidate full Parquet remains on scratch per the runner contract.
