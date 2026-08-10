## Evidence

The corrected implementation read `LOOP_CONTRACT.md`, curated notes, source and corrected FHIR-prober carryover, attempt 0001 implementation/diagnosis, and authoring conventions. It created four ViewDefinitions and `concept.sql` once in attempt 0002 without modifying attempt 0001.

The implementation preserves the exact 23-code filter, source numeric eligibility, specimen grouping, pivots, imputation, scaling, rounding, `TIMESTAMP_NTZ`, nullable `hadm_id` left join, and all 20 manifest columns/types/order. It adds `Quantity.comparator` projection and excludes comparator-bearing synthesized quantities. Static JSON, labels, column order, casts, joins, grouping, and comparator checks passed. No unrepresentable declaration or new notes entry was needed.

Artifacts are `ViewDefinition.lab_observation.json`, `ViewDefinition.patient.json`, `ViewDefinition.specimen.json`, `ViewDefinition.encounter.json`, and `concept.sql` under `mimic-iv/concepts_fhir/concepts/measurement/blood_differential/attempt_0002/`.
