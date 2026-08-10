Evidence block:

- Read the source carryover, LOOP_CONTRACT.md, AGENTS.md, MIMIC_NOTES.md, the local demo Delta warehouse, and the prescription ETL SQL.
- Mapped prescriptions to pharmacy-backed `MedicationRequest` resources and referenced `Medication` resources. Both direct medication references and medication-mix `ingredient.itemReference` branches are required; expand with `UNION ALL` to preserve multiplicity.
- Drug names are preserved in the `mimic-medication-name` identifier value, not reliably in `Medication.code`; route is `dosageInstruction.route.coding.code` under the `mimic-medication-route` system. Patient, hospital Encounter, and ICU Encounter identifiers use the documented identifier systems and UUID reference joins. ICU assignment uses `partOf` and the half-open `[period.start, period.end)` interval.
- Required output conversions: numeric identifier strings to `INTEGER`, route/drug strings to bounded `VARCHAR(255)`, and FHIR datetime strings to `TRY_CAST(... AS TIMESTAMP_NTZ)`.
- Demo probes matched 631 distinct drug strings and all 18,087 expanded `(pharmacy_id, drug, route)` tuples. The source antibiotic filter produced 903 rows, with 944 fragment hits before exclusions. All 154 source name fragments and route literals were checked verbatim.
- Dataset-wide findings promoted/updated in `MIMIC_NOTES.md`: `prescriptions.drug_type` is absent and not exactly recoverable; prescription route and Medication code displays are null. Invalid/incomplete prescription validity periods are omitted by ETL and must not be approximated.
- Carryover written and recorded: `mimic-iv/concepts_fhir/carryover/antibiotic/fhir-prober.md`.
