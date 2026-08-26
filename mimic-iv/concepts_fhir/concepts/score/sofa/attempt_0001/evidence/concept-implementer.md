## Concept implementer evidence

Concept `sofa`, attempt `0001`. The implementer read the source analysis,
FHIR mapping, canonical SQL, curated notes, owned provisional fragment,
manifest, and completed dependency SQL/ViewDefinition artifacts for all 13
dependencies.

Created exactly once:

- `mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0001/ViewDefinition.icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0001/concept.sql`

The implementation uses an ICU Encounter ViewDefinition, opaque equality
joins, published dependency stems, nullable lab joins, exact filters, hourly
boundaries, vasoactive interval semantics, score CASE ordering, 24-row
windows, and the 29 manifest columns. It emits the required
`icu_encounter_key` and `patient_key` provenance keys separately, with
explicit output casts. No unrepresentable declaration was needed.

Result: `uv run mimic_utils lint-sql sofa` reported `sql-lint: sofa: clean`.
No new dataset-wide quirk was discovered or appended. No state transitions,
demo/full runs, or commit were performed.
