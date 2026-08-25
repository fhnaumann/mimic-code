# Evidence — concept-implementer

Concept `gcs`, attempt `0007`.

Authored:

- `ViewDefinition.gcs_observation.json`
- `ViewDefinition.gcs_patient.json`
- `ViewDefinition.gcs_encounter.json`
- `concept.sql`

The implementation filters the exact chartevents coding system and codes, joins Patient and ICU Encounter identifiers, projects Quantity values and the `223900` component text, reproduces the source MAX pivot, strict six-hour previous-row logic, defaults, and ETT branch. The final SELECT emits the eight manifest columns with explicit casts and no resource IDs or key columns. No `unrepresentable.json` was created.

Read the source analysis, fresh FHIR prober, canonical SQL, manifest, curated notes, and relevant fragments. Prober claims were checked against rebuilt Delta/source probes; stale UUID-recovery and label-loss claims were not used.

`uv run mimic_utils lint-sql gcs` reported two legacy `missing-resource-key` violations for the intentionally key-free final output. This evidence records the implementer's report; the orchestrator must resolve the conflict with the authoritative shape contract before freezing the attempt.

No notes fragment was appended.
