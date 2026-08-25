# HPC poller evidence

Concept: `inflammation`  
Attempt: `attempt_0004`  
Job: `30484621`

The Slurm job completed normally and the fetched full-data comparator returned `match`. All 117,898 oracle rows reproduced identically; keyed diff on `specimen_id` had zero differing, null-only, candidate-only, or oracle-only rows. Schema matched, with the three required FHIR key columns present. No divergence exists, so no diagnostician or judge was required. Slurm elapsed time was 92 seconds.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt directory. No SQL/ViewDefinitions were edited.
