# Concept-implementer evidence — meld

The implementer read the canonical source SQL, DAG/manifest, curated notes,
relevant provisional fragments, both meld carryover analyses, canonical
ViewDefinition conventions, and completed dependency attempt shapes. It
authored the following immutable attempt artifacts:

- `ViewDefinition.icu_encounter.json`
- `ViewDefinition.hospital_encounter.json`
- `ViewDefinition.patient.json`
- `concept.sql`

The ICU Encounter view selects the ICU stream by its exact identifier system,
projects the type-prefixed ICU resource key, patient reference key, parent
hospital reference key, period endpoints, and `stay_id` identifier value. The
hospital Encounter and Patient helper views provide the corresponding resource
keys and identifier values. The SQL joins helpers and completed
`first_day_lab`/`first_day_rrt` dependency views on opaque key equality, keeps
the source LEFT-join behavior, preserves the MELD CASE logic, and emits all ten
manifest columns plus `encounter_key`, `icu_encounter_key`, and `patient_key`.
Manifest-typed columns receive explicit casts; resource keys remain verbatim.

`uv run mimic_utils lint-sql meld` passed cleanly. No `unrepresentable.json` was
needed and no new dataset-wide fragment was appended.
