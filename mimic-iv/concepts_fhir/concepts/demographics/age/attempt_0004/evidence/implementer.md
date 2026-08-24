Evidence block

Concept: `age`, attempt `0004`.

Read AGENTS.md, both carryover analyses, `MIMIC_NOTES.md`, the superseded `height.md` fragment, the source SQL, manifest, canonical ViewDefinition example, and relevant prior artifacts. Applied the Patient.birthDate representability, identifier spine, opaque resource-key, hospital Encounter filtering, and `TIMESTAMP_NTZ` rules. The height UUID-recovery recommendation was not used; no fragment was appended.

Written artifacts:
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/ViewDefinition.encounter.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/ViewDefinition.patient.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/concept.sql`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/unrepresentable.json`

The implementation projects Patient and hospital Encounter resources, filters by the hospital identifier system, joins only on opaque resource keys, casts every manifest column, emits both required keys, and uses typed NULLs for `anchor_age` and `anchor_year`. Datetime handling uses `TRY_CAST(... AS TIMESTAMP_NTZ)` with no timezone-converting parser or cast.

JSON syntax validation passed. `uv run mimic_utils lint-sql age` passed cleanly. No full-data correctness is claimed.
