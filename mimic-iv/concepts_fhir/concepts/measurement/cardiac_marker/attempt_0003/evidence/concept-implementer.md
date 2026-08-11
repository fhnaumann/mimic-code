# Evidence: concept-implementer

Concept: `cardiac_marker`; attempt `0003`.

The implementer read the loop contract, Pathling SQL and FHIR mapping skills,
the shared notes and cardiac-marker fragment, both reusable carryover analyses,
the canonical source SQL, and prior attempt artifacts. It created the four
ViewDefinitions and `concept.sql` in this attempt, using exact itemid strings,
specimen grouping, patient/specimen joins, a left encounter join, numeric
Quantity casts, and typed output casts.

The implementation still contains a `COALESCE` fallback from
`effective_datetime` to `effective_period_start` in `concept.sql`. This does
not satisfy the human reopen instruction to use a bare `TRY_CAST` for every
datetime mapping and remove the fallback branch, so the attempt must not pass
to validation. No new dataset-wide quirk was reported and no notes fragment
was appended.

Artifacts produced:

- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `concept.sql`
