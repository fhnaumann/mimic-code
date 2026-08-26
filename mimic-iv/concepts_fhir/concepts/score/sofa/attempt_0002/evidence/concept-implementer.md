## Concept implementer evidence

Concept `sofa`, attempt `0002`, created after the attempt_0001 semantic
diagnosis. Reused the recorded source and FHIR carryover; read the canonical
SQL, curated notes, owned fragment, and immutable attempt_0001 artifacts.

Created exactly once:

- `mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0002/ViewDefinition.icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/score/sofa/attempt_0002/concept.sql`

The corrected implementation preserves all 29 oracle columns plus the required
`icu_encounter_key` and `patient_key`, all published dependency stems, filters,
joins, interval boundaries, aggregations, rolling windows, and final casts.
The cardiovascular thresholds now explicitly use `CAST(15 AS FLOAT)`,
`CAST(0.1 AS FLOAT)`, `CAST(5 AS FLOAT)`, and `CAST(0 AS FLOAT)` with unchanged
strict operators and CASE ordering. No resource-id recovery or precision
manufacturing was introduced; no carryover stage was invalidated.

Result: `uv run mimic_utils lint-sql sofa` passed. No demo/full run, state
transition, commit, or unrepresentable declaration was created. Attempt_0001
remains untouched and no notes fragment entry was appended.
