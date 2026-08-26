Concept `sepsis3`; attempt_0001 full-data poll.

The existing Slurm job `30542702` completed cleanly. `uv run mimic_utils
hpc-poll sepsis3` fetched and verified fresh `comparison.full.json`,
`run_meta.full.json`, and `hpc_accounting.json`; this was not a crash or
timeout and no relaunch occurred. Slurm elapsed time was 2,686 seconds.

Comparator verdict: `review`, tier `contested`; both
`divergence.judge_required` and `divergence.diagnostician_required` are true.
Schema matched: all 14 manifest columns plus required extra key columns
`icu_encounter_key` and `patient_key`, no missing or incompatible types.

Full row counts (not gated): oracle 32,971, candidate 32,794, delta -177;
32,414 rows identical (98.31%). Divergence classes:
- 380 `differing_conflict`
- 177 `only_oracle`
- 0 `differing_null_only`
- 0 `only_candidate`

Conflict columns: `antibiotic_time` 367, `suspected_infection_time` 74,
`culture_time` 43, `sofa_score` 25, `cardiovascular` 20, `sofa_time` 20,
`respiration` 12, `coagulation` 7, `cns` 6, `liver` 4, `renal` 1. The
comparator attempted DST attribution over the whole conflict set but
attributed 0/380, leaving a residual of 380 and tier `contested`; natural key
is `[stay_id]`, so key attribution was not attempted.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/sepsis/sepsis3/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/sepsis/sepsis3/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/sepsis/sepsis3/attempt_0001/hpc_accounting.json`
