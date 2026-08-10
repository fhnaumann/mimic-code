Evidence block — concept `acei`, stage `concept-implementer`.

Read LOOP_CONTRACT.md, MIMIC_NOTES.md, the reusable source and FHIR analyses,
the oracle manifest, source SQL, and prior attempt evidence. Created the
write-once implementation artifacts:

- `ViewDefinition.medication_request.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `concept.sql`

The implementation joins MedicationRequest to Medication through FHIR
reference keys, recovers numeric identifiers from identifier values, filters
the exact medication-name system with all ten ACEI predicates, and preserves
missing validity periods as timestamp NULLs without using `authoredOn`. No
`unrepresentable.json` applies. Static JSON, label/name, and manifest-order
checks passed.

The embedded Spark check exposed a fixable implementation issue: Spark 4.0.2
rejects the unsized `CAST(... AS VARCHAR)` used for the output drug name with
`DATATYPE_MISSING_SIZE`; the correction is `VARCHAR(255)` in a new immutable
attempt. The current artifact was not edited. The dataset-wide requirement
was added to `mimic-iv/concepts_fhir/MIMIC_NOTES.md` as “Spark requires a length
for VARCHAR casts.”
