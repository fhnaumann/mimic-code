# Source analyst evidence — `first_day_sofa`

## Findings

- Canonical SQL: `mimic-iv/concepts/firstday/first_day_sofa.sql`; DAG level 2; SHA256 `e56ae4c67d7b19bf8d47f262011bcd888bdb04160b1e9ce744423243b867892e`.
- Natural grain/key: one row per `mimiciv_icu.icustays.stay_id`; oracle has 73,181 rows.
- Direct source: `icustays(subject_id, hadm_id, stay_id, intime)`.
- Candidate dependencies: `norepinephrine`, `epinephrine`, `dobutamine`, `dopamine`, `bg`, `ventilation`, `first_day_vitalsign`, `first_day_lab`, `first_day_urine_output`, and `first_day_gcs`. They must be consumed through completed dependency views, not rederived.
- Output columns: `subject_id`, `hadm_id`, `stay_id`, `sofa`, `respiration`, `coagulation`, `liver`, `cardiovascular`, `cns`, `renal`, plus required opaque `patient_key`, `encounter_key`, and `icu_encounter_key` columns.
- Core joins/windows: medication starttimes and blood gases use inclusive `[-6 hours, +1 day]` around ICU `intime`; ventilation is an inclusive interval overlap by `stay_id`; blood gases join by `subject_id` and require `specimen = 'ART.'`; ventilation requires `ventilation_status = 'InvasiveVent'`.
- Aggregations: conditional `MAX` per vasoactive agent, conditional `MIN` P/F values by ventilated status, then ordered SOFA threshold CASE expressions. Component scores remain nullable; total SOFA sums `COALESCE(component, 0)`.
- Essential risks: ICU/event timestamps and windows, `ART.` and `InvasiveVent` discriminators, medication starttime/rate, dependency threshold values, and ICU/hospital identifier mapping can alter row inclusion or score branches.
- No direct itemid/ICD/LOINC filter occurs in this SQL; dependency-owned code sets remain in dependency ports.

## Evidence block

Read/checks: read `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, `MIMIC_NOTES.d/README.md`, relevant first-day and dependency fragments, the DAG, oracle manifest, canonical `first_day_sofa.sql`, and ICU DDL. Verified DAG path, source SHA, dependency list, output schema, natural key, joins, windows, literals, aggregations, and score branches. No SQL was executed and no attempt artifact was edited by the analyst. Reusable analysis artifact: `mimic-iv/concepts_fhir/carryover/first_day_sofa/source-analyst.md`; carryover ledger was recorded at `mimic-iv/concepts_fhir/carryover/first_day_sofa/carryover.json`.
