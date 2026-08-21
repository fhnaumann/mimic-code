Concept `suspicion_of_infection`, attempt `0001`; concept-implementer evidence.

Authored write-once artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.encounter.json`
- `ViewDefinition.encounter_icu.json`
- `ViewDefinition.micro_test.json`
- `ViewDefinition.micro_org.json`
- `ViewDefinition.micro_specimen.json`
- `concept.sql`

The SQL consumes the completed `antibiotic` dependency through `FROM antibiotic`, preserves its opaque resource keys, and recovers numeric identifiers through Patient/Encounter identifier projections. Microbiology uses specimen-level aggregation, test `hasMember` organism joins, exact coding-system bindings, organism exclusion `90856`, subject-only joins, date-only handling, 72-hour/24-hour windows, source ordering, and final LEFT JOIN semantics. Manifest columns are explicitly cast, including bounded VARCHAR and `TIMESTAMP_NTZ` datetime outputs; no `unrepresentable.json` was warranted. Resource IDs were not parsed or reconstructed.

The implementer reports demo execution with 903 rows and compatible types and reports `uv run mimic_utils lint-sql suspicion_of_infection` passed cleanly. No new dataset-wide note was appended; the inherited human-accepted `antibiotic` validity-endpoint gap remains at the dependency boundary and was not estimated or hidden.

Artifacts are under `mimic-iv/concepts_fhir/concepts/sepsis/suspicion_of_infection/attempt_0001/`.
