# Evidence: concept-implementer

Concept: `cardiac_marker`; attempt `0004`.

The implementer read the loop contract, Pathling/FHIR mapping skills, canonical
SQL, oracle manifest, shared notes and fragments, reusable source/prober
analyses, and attempts 0002/0003 evidence. It created the four ViewDefinitions
and `concept.sql` using the exact lab-item system and string codes `51003`,
`50911`, and `50963`, patient/specimen identifier joins, a LEFT hospital
Encounter join, Quantity-to-DOUBLE casts, specimen grouping/MAX pivots, bounded
VARCHAR casts, and typed output casts.

The datetime mapping now uses only bare
`TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)`; the rejected Period fallback
is absent. JSON, naming/resource, manifest-column-order, cast-coverage,
UUID-output, forbidden-fallback, and `git diff --check` checks passed. No new
dataset-wide quirk was established and no notes fragment was appended.

Artifacts produced:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `ViewDefinition.lab_observation.json`
- `concept.sql`
