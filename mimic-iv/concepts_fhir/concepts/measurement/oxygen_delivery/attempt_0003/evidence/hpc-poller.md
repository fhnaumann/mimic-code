Evidence block

- Concept: `oxygen_delivery`, attempt `0003`; job `30111381`.
- Poll outcome: `complete`; Slurm state `COMPLETED`, no fatal markers, no resubmission, and artifacts fetched.
- Comparator verdict: `review`, tier `attributed`; `divergence.diagnostician_required=false`, `divergence.judge_required=true`. The diagnostician is skipped; the equivalence judge is required.
- Schema matched. The manifest-required extra key columns are `patient_key` and `icu_encounter_key`.
- Row counts: oracle 601,546, candidate 601,543, delta -3; row count is reported, not gated. Identical rows: 601,509/601,546 (99.99%).
- Divergence: 3 `differing_conflict`, 34 `only_oracle`, and 31 `only_candidate`; all were attributed over the complete set to the upstream America/New_York `TIMESTAMPTZ` DST shift, with 31 re-paired and 3 key collisions and zero residuals. No gap-shaped or unresolvable residual remained.
- The judge bar requires confirming that the cited upstream ETL statement writes the FHIR-sourced elements and that the 0.006% affected fraction fits DST-gap rarity; it must not accept resource-ID reconstruction.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/measurement/oxygen_delivery/attempt_0003/`.
