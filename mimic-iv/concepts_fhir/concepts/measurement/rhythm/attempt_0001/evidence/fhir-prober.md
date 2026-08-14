# FHIR-prober evidence — rhythm

The prober read the source carryover, canonical SQL, `MIMIC_NOTES.md`, relevant
fragments, the reference ViewDefinition, and MIMIC-FHIR ETL SQL, then queried
the authoritative demo Delta warehouse with embedded Pathling/Spark. It
confirmed the chartevents coding system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and exact
codes 220048, 224650, 224651, 226479, and 226480. All 24,832 targeted source
rows had matching FHIR codings, Patient/ICU Encounter references, effective
dateTime values, and valueString text, including trailing spaces. The mapping
uses opaque reference-key equality joins to Patient and ICU Encounter, then
casts identifier values to integer; it does not parse IDs.

The probe confirmed repeated rows must survive until aggregation and measured
four source rows/two groups affected by DST normalization in the demo. It found
no selected NULL values or hard-coded duplicate exclusions in the demo target.
It appended the dataset-wide `Observation.issued` finding to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/rhythm.md` and wrote reusable mapping to
`mimic-iv/concepts_fhir/carryover/rhythm/fhir-prober.md`, recorded in the
carryover ledger. The original charttime remains potentially unrepresentable
at DST-gap keys; this is reserved for the full comparator and judge.
