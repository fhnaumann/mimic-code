Evidence block

Concept: `age`, attempt `0004`, full run 1.

`uv run mimic_utils hpc-poll age` completed with poll outcome `complete`; the comparison was fetched after the Slurm job exited normally. Job `30470367` completed with 24 seconds of Slurm elapsed time. No second job was launched.

Comparator verdict: `review`, tier `gap_shaped`, not a failure. The comparison is keyed on `hadm_id`; `judge_required` is true and `diagnostician_required` is false, so the next stage is the equivalence judge directly.

Full-data counts: oracle 431,231 rows, candidate 431,231 rows, delta 0 (row count is reported but not gated); schema match true; 431,231 `differing_null_only`, 0 `differing_conflict`, 0 `only_candidate`, 0 `only_oracle`; 0 full-tuple identical rows and 431,231/431,231 (100.00%) identical on representable columns. `anchor_age` and `anchor_year` were confirmed 100% NULL in the candidate under the declared unrepresentability contract. No declaration violations occurred.

The judge bar is: cite the absent FHIR element/path, show it explains the magnitude and shape, and confirm every defensible mapping was tried. There are no divergent dependencies.

Artifacts fetched or written:
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/hpc_accounting.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/hpc_job.json`
- Remote candidate remains at `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/candidate.full.parquet`.

No dataset-wide quirk was newly established and no notes fragment was appended.
