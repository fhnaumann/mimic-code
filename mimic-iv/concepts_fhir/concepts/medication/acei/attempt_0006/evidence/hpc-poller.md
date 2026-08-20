# HPC poller evidence — acei attempt 0006

- Job `30230354` completed successfully; Slurm accounting reports 33 seconds
  elapsed.
- `uv run mimic_utils hpc-poll acei` fetched fresh full-data artifacts.
- Comparator verdict: `review`, tier `gap_shaped`; this is a semantic verdict,
  not a polling failure.
- Oracle and candidate each have 112,014 rows. Schema matches, including the
  required `patient_key` and `encounter_key` support columns.
- The unkeyed residual paired 1:1 on `(acei, hadm_id, subject_id)`: 102,948
  rows identical, 9,059 `differing_null_only` endpoint differences, and 7
  conflicts. All 7 conflicts were machine-attributed to the upstream
  `TIMESTAMPTZ` DST-gap transformation with zero residual; the comparator set
  `diagnostician_required=false` and `judge_required=true`.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/medication/acei/attempt_0006/hpc_accounting.json`
