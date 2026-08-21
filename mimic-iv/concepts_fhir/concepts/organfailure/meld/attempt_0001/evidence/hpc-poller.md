# HPC-poller evidence — meld

The recorded Slurm job `30315052` completed and the CLI fetched a fresh full
comparison. The comparator returned an exact `match` on the keyed join
`stay_id`: all 73,181 oracle rows and all 73,181 candidate rows matched
identically, with zero `only_oracle`, `only_candidate`,
`differing_conflict`, or `differing_null_only` rows. The schema matched, with
only the expected required FHIR key columns (`encounter_key`,
`icu_encounter_key`, `patient_key`) beyond the ten compared columns.

No divergence tier was present (`none`); `judge_required` and
`diagnostician_required` were both false, so no judge or diagnostician was
spawned. The full run consumed one HPC run and reported 1,054 seconds Slurm
elapsed time (1,050.02 seconds execute, 1.148 seconds compare).

Fetched artifacts:

- `mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0001/hpc_accounting.json`

This is the full-data correctness result; no clinical judgment was required.
