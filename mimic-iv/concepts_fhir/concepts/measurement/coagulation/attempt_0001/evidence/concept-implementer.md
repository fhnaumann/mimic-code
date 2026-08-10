Concept: coagulation, attempt_0001.

The implementer created `ViewDefinition.lab_observation.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, `ViewDefinition.specimen.json`, and `concept.sql`. The ViewDefinitions use the exact labevents coding system and six source itemids, identifier.value for MIMIC IDs, UUID/reference keys only for joins, the specimen identifier as the grouping key, and optional hospital Encounter data through a left join. The SQL filters non-null Quantity values while excluding comparator-synthesized and string values, uses TIMESTAMP_NTZ for effective time, reproduces independent specimen-level MAX pivots, and explicitly casts all ten manifest columns.

The manifest shape and filename/ViewDefinition-name alignment were checked. No unrepresentable declaration was needed. The existing coagulation notes fragment already records the comparator-synthesis safeguard; no additional dataset-wide finding was appended.
