# HPC poller evidence

Attempt `0002` job `29782598` completed normally (Slurm elapsed 86 seconds)
with fresh comparison artifacts. Verdict: `review`, tier `attributed`,
`judge_required=true`, `diagnostician_required=false`. Schema matched exactly;
candidate and oracle each had 117,898 rows, with 117,897 identical. The sole
`differing_conflict` was `charttime` at `specimen_id=20137346`, oracle
`2150-03-08 02:07` versus candidate `03:07`, fully replayed as the
America/New_York DST-gap cast. Correct attribution citations now include
`mimic-fhir/sql/fhir_observation_labevents.sql:15,121` and
`mimic-fhir/sql/fhir_specimen_lab.sql:18,58` (plus the generic known sites).

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in attempt `0002`; candidate full parquet remains on
scratch.
