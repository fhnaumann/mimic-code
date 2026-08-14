## Evidence

The implementer read both reusable analyses, the curated notes, the rrt
fragment, and relevant provisional fragments. It produced four ViewDefinitions
and `concept.sql`, preserving the source itemids, predicates, inclusive range
overlay, `UNION DISTINCT`, and five manifest columns with explicit casts. JSON
validation and `uv run mimic_utils lint-sql rrt` passed. No opaque resource-id
construction or unrepresentable declaration was used.

Artifacts:
- `ViewDefinition.rrt_encounter.json`
- `ViewDefinition.rrt_observation.json`
- `ViewDefinition.rrt_medication_administration.json`
- `ViewDefinition.rrt_procedure.json`
- `concept.sql`
