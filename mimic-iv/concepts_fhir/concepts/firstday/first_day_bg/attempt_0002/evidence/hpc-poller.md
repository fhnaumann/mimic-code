# Evidence: hpc-poller (`first_day_bg`, attempt 0002)

The poller followed `hpc_job.json` for Slurm job `30238491`; it completed
normally with Slurm elapsed time 226 seconds. The full comparator returned
`review`, tier `contested`, with both `judge_required: true` and
`diagnostician_required: true`.

Full-data schema identity passed. All 44 manifest columns were present with
compatible types, and the required opaque key columns `patient_key` and
`icu_encounter_key` were present. Candidate and oracle row counts were both
73,181; row count was reported, not gated. The keyed diff reproduced 73,180
rows identically and found one `differing_conflict`, with no
`only_oracle`, `only_candidate`, or `differing_null_only` rows. Comparator
attribution was not attempted because the final concept output has no
datetime column.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

The contested review requires the mismatch diagnostician before the
equivalence judge. No terminal state transition or commit was made.
