# Concept implementer evidence

Evidence block

Concept: `vasoactive_agent`; attempt: `0001`.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/ViewDefinition.medication_administration.json`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/ViewDefinition.encounter_icu.json`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/concept.sql`

The implementation projects all seven exact ICU medication codes and systems, both `effective[x]` variants, Quantity rate/dose fields, opaque reference keys, and ICU Encounter identifiers. SQL preserves the seven dependency views, 14-boundary `UNION DISTINCT`, `LEAD` interval construction, seven containment joins, manifest casts, and support keys.

No `unrepresentable.json` was needed. Row-level missing `patientweight`/`starttime` values are not declared or estimated.

Applied `MIMIC_NOTES.md` entries on identifier spines, opaque keys, polymorphic fields, Quantity typing, datetime handling, ICU Encounter systems, and omitted `linkorderid`. Read `README.md` and medication fragments for dobutamine, dopamine, epinephrine, milrinone, norepinephrine, phenylephrine, and vasopressin; their claims were cross-checked against the recorded Delta/DuckDB prober results and completed dependency attempts. No fragment was appended.

Lint: `uv run mimic_utils lint-sql vasoactive_agent` passed cleanly. No state transitions or commits were performed.
