Evidence block

Concept: `chemistry`; attempt: `attempt_0002`; Slurm job `29679066`.

`uv run mimic_utils hpc-poll chemistry` completed after two polls. Outcome: `complete`; no fatal marker was encountered and the job left the queue normally. Fresh full artifacts were fetched. Comparator verdict: `review`, not a crash and not a `mismatch`.

Schema identity matched with no missing, extra, or incompatible columns. Candidate and oracle row counts were both 3,811,523; row count is reported only and not gated. Divergence tier is `contested`: 3,811,523 `differing_conflict` rows, all isolated to `charttime`; there were no `only_oracle`, `only_candidate`, or `differing_null_only` rows, and no unrepresentable declaration. Samples showed every other column agreeing while candidate charttime differed by a time-of-day offset.

Artifacts fetched:
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002/run_meta.full.json`

`candidate.full.parquet` remains on scratch. Next required phase is diagnosis of the contested charttime divergence before convening the judge. No implementation or notes files were modified by polling.
