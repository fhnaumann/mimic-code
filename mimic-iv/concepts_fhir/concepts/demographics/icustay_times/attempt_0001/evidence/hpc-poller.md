# HPC poller evidence

Concept: `icustay_times`; attempt: `0001`.

Slurm job `29781001` completed successfully after two polls. The full
comparator verdict is `match`; no judge or diagnostician was required. The
candidate reproduced 73,181 of 73,181 oracle rows identically (100%), with
candidate and oracle counts equal and schema identical across
`subject_id`, `hadm_id`, `stay_id`, `intime_hr`, and `outtime_hr`, keyed by
`stay_id`. Divergence tier is `none`.

Fetched artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

All are under
`mimic-iv/concepts_fhir/concepts/demographics/icustay_times/attempt_0001/`.
Slurm elapsed time was 96 seconds.
