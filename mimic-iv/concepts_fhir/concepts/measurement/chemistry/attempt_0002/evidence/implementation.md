Implementation evidence block

Concept: `chemistry`. Attempt 0001 contained an initial implementation that failed before the demo gate because of an invalid Spark datetime pattern; it was not edited. The controller-created corrected immutable attempt is attempt 0002.

Artifacts:
- `ViewDefinition.lab_observation.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.specimen.json`
- `concept.sql`

The port uses Observation, Patient, Encounter, and Specimen projections. It filters all twelve literal chemistry itemids by the lab coding system and string codes, preserves specimen grouping and MAX pivots, uses LEFT JOIN Encounter for nullable `hadm_id`, excludes synthesized comparator/text values, and casts all 17 manifest columns explicitly. The ViewDefinition labels match the SQL temp-view names. No `unrepresentable.json` was required.

The corrected attempt's demo execution produced the expected 18-column shape and 3,289 demo rows; row count was not treated as a gate. Applied `MIMIC_NOTES.md` guidance on identifier spines, verbatim itemid codes, specimen grouping, incomplete Observation encounters, Quantity string aliases, polymorphic effective times, and `TIMESTAMP_NTZ` datetime handling. The implementation stage appended the dataset-wide Spark datetime-pattern finding to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/chemistry.md`. `MIMIC_NOTES.md` was not edited.

Artifact paths: `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002/ViewDefinition.*.json`, `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002/concept.sql`.
