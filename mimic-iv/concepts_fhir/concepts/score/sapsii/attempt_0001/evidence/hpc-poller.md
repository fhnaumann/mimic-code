# HPC-poller/comparator evidence — sapsii attempt_0001

Existing Slurm job `30534540` completed normally and the poller fetched
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`. The
deterministic full-data comparator returned `match`: all 73,181 of 73,181
oracle rows reproduced identically (100.00%), keyed on `stay_id`, with zero
`only_oracle`, `only_candidate`, `differing_null_only`, or
`differing_conflict` rows. Schema matched; the three extra columns
`encounter_key`, `icu_encounter_key`, and `patient_key` are the required FHIR
key companions. The artifact has no divergence tier and both judge/diagnosis
flags are false, so no diagnostician or equivalence judge is allowed or
needed. Candidate and oracle row counts were both 73,181 (reported only).

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in the attempt directory. Slurm elapsed time was 1,563
seconds and the job state was COMPLETED. This is the exact full-data verdict;
the demo shape gate was not used as correctness evidence.
