# HPC poller evidence — `first_day_height`

Polled job `30241742` with `uv run mimic_utils hpc-poll first_day_height`.
The job completed cleanly and fetched the full comparison artifacts. The
deterministic comparator returned `match`; the judge and diagnostician were
not called.

Full data reproduced 73,181/73,181 oracle rows identically (100.00%), with
candidate and oracle row counts both 73,181. Schema matched, including
`subject_id`, `stay_id`, `height`, `patient_key`, and `icu_encounter_key`; the
types were INTEGER/INTEGER/DECIMAL(38,2) plus string key columns. All diff
classes (`only_oracle`, `only_candidate`, `differing_conflict`, and
`differing_null_only`) were zero. `divergence.tier` was `none` and no judge or
diagnostician was required.

Fetched artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

They are under
`mimic-iv/concepts_fhir/concepts/firstday/first_day_height/attempt_0001/`.
