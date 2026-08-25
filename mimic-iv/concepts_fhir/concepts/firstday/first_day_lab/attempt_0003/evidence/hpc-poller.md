# Full-data poll evidence

- Concept: `first_day_lab`, attempt `0003`, job `30491352`.
- Poll outcome: `complete`; Slurm state `COMPLETED` with elapsed time 1562 s.
- Comparator verdict: `match`.
- Keyed diff: `stay_id`; 73,181/73,181 oracle rows reproduced identically.
  `differing_conflict`, `differing_null_only`, `only_candidate`, and
  `only_oracle` were all zero; `identical` was 73,181.
- Schema matched. The two additional columns, `icu_encounter_key` and
  `patient_key`, are the manifest-declared key columns.
- No judge or diagnostician was required.
- Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and
  `hpc_accounting.json`.
