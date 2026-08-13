# FHIR-prober evidence — neuroblock

Read the source carryover, LOOP_CONTRACT.md, MIMIC_NOTES.md, relevant
provisional fragments, and ICU MedicationAdministration/Encounter ETL SQL.
Probed the authoritative demo Delta with embedded Pathling 9.6.0/Spark 4.0.2.
Mapped the source to ICU MedicationAdministration, exact system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`, and codes
`222062` and `221555`; the requested codes are empty in the 100-patient demo,
while the full manifest contains 14,174 rows. Confirmed context-to-ICU
Encounter equality joins, string Encounter identifiers requiring an INTEGER
cast, Quantity aliases materializing as strings, Period start/end for the
rate-bearing branch, and direct datetime handling. Confirmed no independent
orderid element or request identifier exists; resource IDs remain opaque.

Reusable mapping was written to
`mimic-iv/concepts_fhir/carryover/neuroblock/fhir-prober.md` and recorded. The
stage appended dataset-wide findings to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/neuroblock.md` about absent orderid,
one-coding-per-resource, and conditional effective/Quantity branches.
