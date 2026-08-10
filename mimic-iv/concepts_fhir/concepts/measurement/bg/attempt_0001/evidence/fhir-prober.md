# FHIR-prober evidence — bg

**Read and checked:** `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`,
`carryover/bg/source-analyst.md`, canonical and local Observation
ViewDefinitions. Probed embedded Pathling/Spark over the demo Delta warehouse;
no HTTP server was used. `bg` is unkeyed and must use full-tuple multiset
comparison; the oracle has 511,637 rows.

**Resource mappings:** lab events map to `Observation` with the
`mimic-observation-labevents` profile and d-labitems code system; chart events
map to `Observation` with `mimic-observation-chartevents` and the chartevents
d-item code system. Lab `specimen_id` maps through Observation.specimen to
Specimen identifier system `.../identifier/specimen-lab`. Patient, hospital
Encounter, and Specimen joins use `getReferenceKey()` UUIDs for joins and
identifier values for emitted numeric IDs. `subject_id` and `hadm_id` are
string identifiers cast to INTEGER, with hospital Encounter as a left join.

**Field mappings:** item codes come from `code.coding` (`code`, `system`,
`display`); `charttime` comes from `effective.ofType(dateTime)` and must be
cast to `TIMESTAMP_NTZ`; numeric values come from
`value.ofType(Quantity).value`; item 52033 uses
`value.ofType(string)` for specimen text. The mapped itemids are the source
analyses' blood-gas numeric fields, including PO2, PCO2, FiO2, pH, bicarbonate,
hematocrit, hemoglobin, lactate, glucose, and the remaining pivots. Chart 220277
supplies SpO2 (average by patient/time, newest within 2 hours); chart 223835
supplies normalized FiO2 (newest positive value within 4 hours). The derived
`aado2_calc` is DECIMAL(38,4), and `pao2fio2ratio` is DOUBLE.

**Probe results:** 23,992 target Observations were found (8,706 lab and 15,286
chart). All had code/system/display and dateTime effective values; Period and
instant variants were absent. Quantity values covered 22,957 rows and string
values 1,035. Specimen/item/subject/time/numeric mapping agreed with DuckDB for
8,706/8,706 lab rows. Direct hospital Encounter IDs agreed for 8,024/8,024
linked rows; 682 source rows had null `hadm_id`. Item 50807 had no demo rows.

**Dataset-wide findings promoted:** updated the Observation profile note to
document warehouse-version-dependent profile metadata and code-system
discrimination, and added that `Lab Observation.specimen` preserves the source
specimen identifier. Existing notes on identifiers, timestamps, polymorphic
values, and incomplete lab Encounter references were reused.

**Artifacts:**

- `mimic-iv/concepts_fhir/carryover/bg/fhir-prober.md`
- `mimic-iv/concepts_fhir/carryover/bg/carryover.json`
- updated `mimic-iv/concepts_fhir/MIMIC_NOTES.md`
