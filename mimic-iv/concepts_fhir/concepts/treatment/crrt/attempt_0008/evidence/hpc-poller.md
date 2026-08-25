# HPC-poller evidence — crrt attempt_0008

- Job `30484176` completed successfully after 2 polls; no fatal markers or
  timeout.
- Full comparator verdict: `match`; schema matched.
- Keyed diff used `[stay_id, charttime]` and reproduced 287,152/287,152 oracle
  rows identically (100.00%). All divergence classes were empty.
- Candidate row count was 287,152 versus oracle 287,152 (informational).
- Required key columns `icu_encounter_key` and `patient_key` were present and
  accepted by the schema gate.
- Slurm elapsed runtime: 101 seconds.
- Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and
  `hpc_accounting.json` in this attempt.

Because the verdict was an exact full-data `match`, no diagnostician or
equivalence judge was required.
