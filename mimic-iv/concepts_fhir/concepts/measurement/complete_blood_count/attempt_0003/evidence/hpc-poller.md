Evidence block — full-data poll, `complete_blood_count`

- Attempt: `attempt_0003`; job `30105580`.
- Poll outcome: `complete`; Slurm state `COMPLETED`, 117 seconds elapsed; comparison artifacts were fetched.
- Comparator verdict: `review`, tier `attributed`; `diagnostician_required: false`, `judge_required: true`.
- Schema matched. Oracle and candidate row counts both 3,362,503 (reported, not gated). 3,362,299 rows were identical (99.99%).
- Diff classes: `only_oracle` 0, `only_candidate` 0, `differing_null_only` 0, `differing_conflict` 204. All 204 conflicts were on `charttime` and machine-attributed to `upstream_timestamptz_dst_shift`; attribution was complete with zero residual rows.
- The comparator cited upstream ETL locations including `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` and `mimic-fhir/sql/fhir_specimen_lab.sql:18,58`; the judge must still confirm provenance and rarity.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in `mimic-iv/concepts_fhir/concepts/measurement/complete_blood_count/attempt_0003/`.
- No implementation artifacts were edited and nothing was committed.
