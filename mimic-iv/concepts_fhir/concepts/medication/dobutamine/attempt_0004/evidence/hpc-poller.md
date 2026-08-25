## Evidence

- Concept: dobutamine
- Attempt: attempt_0004
- Stage: hpc-poller
- Read/checks: Polled Slurm job `30484229` with `uv run mimic_utils hpc-poll dobutamine`; fetched and inspected `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
- Result: job outcome `complete`; comparator verdict `review`, tier `gap_shaped`, schema matched. `differing_null_only=8513` on declared `linkorderid`; `only_oracle=0`, `only_candidate=0`, `differing_conflict=0`; all 8513 representable rows matched (100% representable fraction). Candidate and oracle row counts were both 8513 and are non-gating.
- Routing: `judge_required=true`; `diagnostician_required=false`, so no diagnostician is spawned. The judge must rule on the declared absence of `MedicationAdministration.identifier`/inputevent linkage.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_accounting.json` in this attempt directory. Slurm elapsed time was 28 seconds.
- Dataset-wide quirk check: no new quirk; the absent ICU inputevent identifier is already recorded in this concept's fragment and corroborated by the full comparison.
