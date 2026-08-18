Evidence block

- Concept: `cardiac_marker`; attempt `0005`; job `30103719`.
- Outcome: `complete`; Slurm state `COMPLETED`; full comparison artifacts fetched.
- Verdict: `review`; `divergence.tier = attributed`; `diagnostician_required = false`; `judge_required = true`.
- Row counts: oracle 295,246 and candidate 295,246; delta 0 (reported, not gated). Identical rows 295,228 (99.99%).
- Diff: 18 `differing_conflict` rows, zero `only_oracle`, zero `only_candidate`, zero `differing_null_only`, and zero unrepresentable exclusions. All 18 conflicts are machine-attributed to `upstream_timestamptz_dst_shift` on `charttime`, with residual 0/18.
- The comparator cites upstream `mimic-fhir` datetime casts, including `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` and `mimic-fhir/sql/fhir_specimen_lab.sql:18,58`, among its attribution citations. The judge must confirm provenance and DST-gap rarity; no diagnostician is spawned.
- Schema matched: the seven compared columns are compatible and the three manifest-declared key columns are present.
- Slurm elapsed: 94 seconds; run metadata execute 89.574 seconds plus compare 1.399 seconds.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/measurement/cardiac_marker/attempt_0005/`.
