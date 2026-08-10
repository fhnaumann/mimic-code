Evidence block:

- Concept/file: `medication/antibiotic` — `mimic-iv/concepts/medication/antibiotic.sql` (203 lines). DAG node level 0, no dependencies, dependent `suspicion_of_infection`.
- Tables: `mimiciv_hosp.prescriptions` (CTE `abx` and main `pr`) and `mimiciv_icu.icustays` (`ie`).
- Output: `subject_id` INT, `hadm_id` INT, nullable `stay_id` INT, `antibiotic` drug string, `route` string, and `starttime`/`stoptime` TIMESTAMP.
- Logic: excludes `drug_type = 'BASE'`, non-administration routes (`OU`,`OS`,`OD`,`AU`,`AS`,`AD`,`TP`), ear/eye routes, and cream/desensitization/ophth oint/gel drugs; classifies using 154 verbatim drug-name LIKE fragments (including duplicate `septra` and `trimethoprim` fragments); retains `abx.antibiotic = 1`.
- Join: LEFT temporal join to `icustays` by `hadm_id`, with `pr.starttime >= ie.intime AND pr.starttime < ie.outtime`; final `SELECT DISTINCT` and no derived dependency.
- Coding: no itemid/ICD; the source specification is free-text drug substrings plus route and `drug_type` literals.
- Carryover written: `mimic-iv/concepts_fhir/carryover/antibiotic/source-analyst.md` and recorded with `mimic_utils carryover-record antibiotic --stage source-analyst`.
