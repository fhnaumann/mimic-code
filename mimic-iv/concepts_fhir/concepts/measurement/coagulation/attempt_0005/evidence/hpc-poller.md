# HPC poller evidence — coagulation attempt 0005

Polled existing Slurm job `30104201` with `uv run mimic_utils hpc-poll
coagulation`; no second launch was performed. Poll outcome was `complete` and
Slurm state was `COMPLETED` after two polls. Final accounting reports 104
seconds elapsed.

The full comparator verdict is `review`, tier `attributed`. Schema passed and
the candidate and oracle each contain 1,543,003 rows. There are 1,542,888
identical rows and 115 `differing_conflict` rows, all on `charttime`; all 115
were replayed to the upstream New York `TIMESTAMPTZ` DST-gap shift with zero
residual. There were no only-oracle, only-candidate, or null-only rows.
`judge_required` is true and `diagnostician_required` is false, so the next
stage is the equivalence judge without a diagnostician.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/hpc_accounting.json`
- `mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/hpc_job.json`

The full candidate Parquet remains on scratch3 per the artifact contract.
