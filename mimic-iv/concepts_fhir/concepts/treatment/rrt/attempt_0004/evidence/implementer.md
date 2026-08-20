Evidence block:

Concept: `rrt`; attempt: `0004`.

Written artifacts:
- `.../attempt_0004/ViewDefinition.rrt_observation.json`
- `.../attempt_0004/ViewDefinition.rrt_medication_administration.json`
- `.../attempt_0004/ViewDefinition.rrt_procedure.json`
- `.../attempt_0004/ViewDefinition.rrt_encounter.json`
- `.../attempt_0004/concept.sql`

The implementation maps Observation, MedicationAdministration, Procedure, and ICU Encounter resources. It applies exact source code/system filters, uses code `227525`, preserves repeated rows, both `UNION DISTINCT` operations, inclusive interval overlays, polymorphic datetime variants, explicit manifest casts, and additive `icu_encounter_key`/`patient_key` outputs. No `unrepresentable.json` was needed.

Read the canonical SQL, manifest, both reusable carryover files, `MIMIC_NOTES.md`, the seven requested provisional fragments, and the fhir-mapping/pathling-sql conventions. Established notes applied include opaque resource keys, identifier spine, TIMESTAMP_NTZ datetime handling, polymorphic COALESCE, Quantity casting, exact coding, repeated chartevents, DST normalization, and bounded VARCHAR casts. Provisional fragments were read as leads and not independently reprobed; no UUID-recovery claims were adopted.

`uv run mimic_utils lint-sql rrt` passed cleanly. No new dataset-wide quirk was established, and `MIMIC_NOTES.d/rrt.md` was not modified.
