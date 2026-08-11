Evidence block — Concept: dopamine.

The prober read the source carryover, curated MIMIC notes, all existing notes fragments, the canonical ViewDefinition reference, ICU MedicationAdministration FSH, and the relevant MedicationAdministration/Encounter ETL SQL. It probed the authoritative demo Delta with embedded Pathling 9.6.0/Spark 4.0.2 and checked the DuckDB demo oracle.

Mapping findings: ICU `inputevents` map to `MedicationAdministration`; `itemid` is the exact code `221662` in system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`. `stay_id` comes through `context.getReferenceKey(Encounter)` and the ICU Encounter identifier system, cast to INTEGER. `rate` and `amount` come from dosage Quantity values and require numeric casts. `starttime`/`endtime` use effective Period start/end, with a dateTime fallback for end, cast to `TIMESTAMP_NTZ` before coalescing. `linkorderid` has no FHIRPath and must be emitted as typed NULL.

The demo had 28 target resources, all with context, ICU Encounter identifier, effective period, rate, amount, and units. `(stay_id,starttime)` was unique 28/28 and stay/start/end agreed with DuckDB. Served Quantity precision was six decimal places; rate and amount were within 1e-6 for every row. The prober identified two dataset-wide findings and appended them to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/dopamine.md`: ICU MedicationAdministration lacks inputevent identifiers, and served ICU MedicationAdministration dosage quantities are limited to six decimal places.

Reusable artifact produced: `mimic-iv/concepts_fhir/carryover/dopamine/fhir-prober.md`, recorded with the carryover ledger. No implementation artifact was created.
