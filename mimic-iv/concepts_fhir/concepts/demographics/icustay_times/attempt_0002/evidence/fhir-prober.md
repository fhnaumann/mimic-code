Concept: icustay_times; attempt: 0002.

The fhir-prober reran the invalidated mapping stage against the authoritative demo Delta using embedded Pathling/Spark. It mapped ICU and hospital Encounter identifier systems, Patient identifier.value, and the chartevents Observation stream filtered by the exact system and code 220045. It confirmed 140 ICU Encounters, 275 hospital Encounters, 100 Patients, and 13,913 target Observations; direct served-time aggregation matched the demo oracle on all five columns. FHIR dateTime is an offset-bearing string and must be read with TRY_CAST(... AS TIMESTAMP_NTZ). Resource IDs were treated as opaque and were not used for charttime recovery.

Reusable artifact: mimic-iv/concepts_fhir/carryover/icustay_times/fhir-prober.md. No dataset-wide note was appended.
