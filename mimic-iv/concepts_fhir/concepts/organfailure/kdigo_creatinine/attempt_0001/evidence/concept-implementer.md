# Concept-implementer evidence

The implementer created three ViewDefinitions and `concept.sql` in the immutable attempt. The port uses the ICU Encounter stream as the driver, the labevents Observation stream filtered by the exact system/code `50912`, patient/time-window association without an Observation-encounter inner join, `(stay_id, charttime)` aggregation, left prior-window enrichments, parent hospital lookup for `hadm_id`, numeric Quantity casting, and `TIMESTAMP_NTZ` wall-clock handling. No unrepresentable declaration was needed. SQL lint was clean.

Artifacts:
- `ViewDefinition.icu_encounter.json`
- `ViewDefinition.hospital_encounter.json`
- `ViewDefinition.lab_observation.json`
- `concept.sql`
