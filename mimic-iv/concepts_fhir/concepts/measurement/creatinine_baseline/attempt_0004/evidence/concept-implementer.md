# Evidence: concept-implementer — creatinine_baseline attempt 0004

Read `AGENTS.md`, the `fhir-mapping` and `pathling-sql` skills, the canonical
`creatinine_baseline` SQL, the full manifest entry, attempt 0003, and the
reusable `source-analyst` and `fhir-prober` carryovers. Read all of
`MIMIC_NOTES.md` and the relevant fragments `creatinine_baseline.md`, `age.md`,
`chemistry.md`, `kdigo_creatinine.md`, and `README.md`. The fragments were
treated as provisional leads; their relevant claims were checked against the
carryovers, prior probe evidence, current dependency SQL, and the current
warehouse-fix instruction. No new dataset-wide quirk was established.

Produced exactly once in this attempt:

- `ViewDefinition.condition.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.patient.json`
- `concept.sql`
- `evidence/concept-implementer.md`

The SQL consumes the completed `age` and `chemistry` temp views. It joins
`age.patient_key` to `patient.patient_key` and `age.encounter_key` to
`encounter.encounter_key` using opaque equality only. The published chemistry
dependency is grouped by its `encounter_key`; the hospital Encounter
identifier value supplies `hadm_id_str` and is the only source of numeric
`hadm_id`. CKD uses the two exact MIMIC diagnosis systems and source prefixes
`585`/`N18`, with the hospital Encounter identifier restriction. The adult
filter, chemistry minimum, MDRD branches, and baseline CASE remain the source
logic.

The outer SELECT emits the manifest columns in order with explicit casts:
`hadm_id`, `gender`, `age`, `scr_min`, `ckd`, `mdrd_est`, and `scr_baseline`,
followed by the required uncast opaque `encounter_key` and `patient_key`.
The ViewDefinitions project resource/reference keys verbatim and identifier
values separately. No resource id is parsed, regenerated, hashed, hardcoded,
or used to infer a source value. No `unrepresentable.json` is needed.

Check: `uv run mimic_utils lint-sql creatinine_baseline` passed cleanly.
No entry was appended to `MIMIC_NOTES.d/creatinine_baseline.md`.
