# Concept-implementer evidence

Concept: `oasis`; attempt: `0002`.

The implementer read the valid source analysis, the superseding FHIR probe,
the curated notes and relevant fragments, and the diagnosis from attempt
0001. It authored fresh immutable artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.hospital_encounter.json`
- `ViewDefinition.hospital_service.json`
- `ViewDefinition.icu_encounter.json`
- `concept.sql`

The hospital Encounter view now projects `priority.coding`; SQL uses the exact
ActPriority system and `EL` code rather than the invalid broad `AMB` class
heuristic. Pre-ICU minutes now truncate both parsed NTZ endpoints to minute
boundaries before `TIMESTAMPDIFF`, matching canonical negative-minute
semantics. All dependency stems, opaque key joins, canonical thresholds,
null handling, score/logistic calculations, manifest casts, and required
resource keys remain preserved. The service-history gap is left explicit and
is not filled with an estimate or false declaration.

`uv run mimic_utils lint-sql oasis` completed cleanly. No new dataset-wide note
was appended. No execution, state transition, or commit was performed by this
stage.
