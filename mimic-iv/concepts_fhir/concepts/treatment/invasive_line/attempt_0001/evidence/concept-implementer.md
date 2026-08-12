# Evidence: concept-implementer

Concept `invasive_line`, attempt `0001`.

Read the canonical source SQL, both invasive-line carryover analyses, `MIMIC_NOTES.md`, relevant notes fragments, the oracle manifest, and ViewDefinition/Pathling authoring conventions. Authored two immutable ViewDefinitions and `concept.sql`. The Procedure view filters all 24 exact itemids and the item coding system, uses `forEachOrNull` for body sites, and projects performed Period choices. The Encounter view exposes the ICU identifier spine. The SQL preserves source CASE mappings and row multiplicity, joins on the Encounter reference key, casts MIMIC identifiers to `INTEGER`, timestamps to `TIMESTAMP_NTZ`, and manifest VARCHAR outputs to bounded `VARCHAR(255)`.

Artifacts produced:
- `ViewDefinition.invasive_line_procedure.json`
- `ViewDefinition.invasive_line_icu_encounter.json`
- `concept.sql`

`uv run mimic_utils lint-sql invasive_line` passed. No `unrepresentable.json` was required. The known four `Right Antecube ` trailing-space values are represented by the served trimmed FHIR value rather than fabricated source whitespace.
