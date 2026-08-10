Evidence block — concept `acei`, stage `concept-implementer`, attempt 0003.

Read AGENTS.md, LOOP_CONTRACT.md, MIMIC_NOTES.md, the source SQL, oracle
manifest, both acei carryover analyses, and all attempt_0002 artifacts and
evidence. Created, once, the corrected implementation artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.medication.json`
- `ViewDefinition.medication_request.json`
- `concept.sql`

The implementation preserves the MedicationRequest-to-Medication reference
joins, identifier-based numeric casts, hospital Encounter filtering, the
medication-name system, all ten ACEI predicates, and nullable TIMESTAMP_NTZ
validity periods. The exact fix is
`CAST(m.drug_name AS VARCHAR(255))`, replacing the Spark-invalid unsized cast
from attempt_0002. No `unrepresentable.json` is required.

Static JSON, mapping, manifest-order, predicate-count, immutability, Spark
parser, and empty-view shape checks passed with schema
`INTEGER, INTEGER, VARCHAR, TIMESTAMP_NTZ, TIMESTAMP_NTZ`. Attempt_0002 and
MIMIC_NOTES.md were not edited; no new note was needed.
