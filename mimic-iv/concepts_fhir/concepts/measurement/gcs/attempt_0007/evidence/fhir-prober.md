# Evidence — fhir-prober

Concept `gcs`, attempt `0007`.

Read the canonical source analysis, full `MIMIC_NOTES.md`, canonical ViewDefinition format, current `mimic-fhir/sql/fhir_observation_chartevents.sql`, and relevant provisional fragments including `gcs.md`, `first_day_gcs.md`, `crrt.md`, `code_status.md`, `cardiac_marker.md`, `oxygen_delivery.md`, `ventilator_setting.md`, and the fragment README. Fragment claims were treated as provisional and checked against served Delta/source data where relevant.

Probed `/Users/nau025/warehouses/mimic-iv-demo/delta` with embedded Pathling 9.6.0/Spark 4.0.2 and DuckDB source data. Confirmed the Observation chartevents mapping, exact item codes `220739`, `223900`, `223901` under `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, identifier/reference joins, and `effective.dateTime` parsed as `TIMESTAMP_NTZ`.

The rebuilt warehouse exposes `Observation.component[].valueString` for item `223900` via the same item coding. Component text was populated on 9,791/9,791 target rows and coexisted with Quantity on 9,791/9,791; component code/system/display matched the Observation code on 9,791/9,791. `No Response-ETT` occurred 1,348 times and `No Response` 78 times, both with Quantity value 1. Source/FHIR agreement was 9,791/9,791 for identifiers, effective datetime, quantity, component text, coding, and display. The prior `gcs_unable` unrepresentability declaration must be removed; derive the exact sentinel and all GCS carry-forward logic from component text. Resource ids were not used for recovery.

The source selected demo rows had no NULL values or duplicate item groups; the global ETL NULL-value omission remains a possible full-data coverage gap but was not exercised in this demo. No new dataset-wide quirk was appended to `MIMIC_NOTES.d/gcs.md` because the component behavior is already documented in curated `MIMIC_NOTES.md`.

Artifact produced/updated by the agent: `mimic-iv/concepts_fhir/carryover/gcs/fhir-prober.md`. This evidence file is the orchestrator's immutable copy of the returned evidence block.
