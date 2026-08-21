# HPC Poller — kdigo_uo attempt_0003

## Job
- concept: `kdigo_uo`
- job id: `30311141` (from `hpc_job.json`)
- outcome: `complete`
- verdict: `review`

## Slurm accounting
- state: COMPLETED
- elapsed: 195 s (Slurm elapsed, `sacct`)
- started: 2026-08-21T11:19:16, ended: 2026-08-21T11:22:31

## Comparator (comparison.full.json)
- schema identity: `match` (types compatible, no missing/incompatible columns; candidate has 2 extra traceability columns `icu_encounter_key`, `patient_key`)
- row count (not gated): oracle 3,321,748 vs candidate 3,321,512 (delta −236)
- identical: 3,320,293 (99.9562%)

## Divergence
- tier: `contested`
- `diagnostician_required`: true
- `judge_required`: true
- reviewable/blocking classes:
  - `differing_conflict` × 1,062 (0.032% of oracle rows) — contested (value conflict, residual 1,060 do not replay the DST shift; only 2 attributed to key collision)
  - `only_oracle` × 393 (attributed to `upstream_timestamptz_dst_shift`) — all replay the shift
  - `only_candidate` × 157 (attributed to `upstream_timestamptz_dst_shift`) — all replay the shift
- key attribution: attempted, complete — key columns `[charttime]`; only_oracle 393, only_candidate 157, collided 236, repaired 157; residual_only_oracle 0, residual_only_candidate 0
- conflict attribution: 2 of 1,062 conflicting rows replay the shift; 1,060 residual, unexplained → tier stays `contested`
- conflicting columns: uo_tm_6hr (415), uo_rt_6hr (400), uo_tm_12hr (370), uo_rt_12hr (337), uo_tm_24hr (322), urineoutput_6hr (299), uo_rt_24hr (276), urineoutput_12hr (252), urineoutput_24hr (207), weight (1)

### ETL citations (attribution)
- mimic-fhir/sql/fhir_observation_chartevents.sql:9,67
- mimic-fhir/sql/fhir_observation_labevents.sql:15,121
- mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65
- mimic-fhir/sql/fhir_specimen_lab.sql:18,58
- mimic-fhir/sql/fhir_encounter.sql:65
- mimic-fhir/sql/fhir_medication_request.sql:43-44
- mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69

## Notes
- review verdict → spawn equivalence judge. Do NOT accept a port recovering the pre-shift key by reconstructing a resource id (ETL inversion, not a mapping).
- Row count reported, not gated.

## Artifacts
- fetched: `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0003/comparison.full.json`
- fetched: `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0003/run_meta.full.json`
- accounting: `/Users/nau025/Documents/mimic-code/mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0003/hpc_accounting.json`