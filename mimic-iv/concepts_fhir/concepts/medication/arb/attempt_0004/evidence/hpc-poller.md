# Evidence — hpc-poller

Concept: `arb`; attempt: `0004`; full run: 1 for this attempt.

`uv run mimic_utils hpc-poll arb` completed normally for Slurm job `30230384`.
The job was `COMPLETED`, with 29 seconds Slurm elapsed time, and fresh full
artifacts were fetched. The comparator verdict was `review` (exit code 2), not
a job failure.

Schema matched exactly, including the expected opaque FHIR key columns. Row
counts were candidate 39,534 and oracle 39,534; this was reported but not
gated. The unkeyed full-tuple residual paired 3,181 substitutions anchored by
`subject_id`, `hadm_id`, and `arb`. Identical rows: 36,353/39,534 (91.95%).

Divergence was tier `gap_shaped`, `judge_required: true`, and
`diagnostician_required: false`. There were 3,179 `differing_null_only`
findings (candidate validity endpoints absent: `starttime` NULL on 3,179 and
`stoptime` NULL on 3,178) corresponding to the omitted invalid/reversed
MedicationRequest validity periods. Two `differing_conflict` values (one
start and one stop) were fully machine-attributed to the upstream
`TIMESTAMPTZ` DST-gap transformation, with zero residual; the artifact carries
the `mimic-fhir` citations. No contested, blocking, or unresolvable findings
remained. The equivalence judge is still required.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

No implementation artifacts were modified, no job was resubmitted, and no
commit was made.
