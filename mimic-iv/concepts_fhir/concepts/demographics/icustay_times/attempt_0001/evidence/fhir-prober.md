# FHIR prober evidence

Concept: `icustay_times`; attempt: `0001`.

The probe mapped ICU `Encounter` to `mimiciv_icu.icustays` and chartevents
`Observation` to `mimiciv_icu.chartevents`. `subject_id` comes from the
Patient identifier spine, `hadm_id` from ICU Encounter `partOf` to hospital
Encounter, and `stay_id` from ICU Encounter's `encounter-icu` identifier.
Heart-rate `220045` uses the chartevents code system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`, with
effective `dateTime` and Quantity value.

The target code was confirmed at 13,913 resources with coding ratio 1.000.
ICU identifiers, partOf links, periods, patient identifiers, observation
references, effective times, and quantities were populated for the 140 demo
stays. Source/FHIR checks agreed for all 140 demo stays on IDs and MIN/MAX
times. Two demo DST-normalized heart-rate observations require conditional
UUID-v5 recovery from 03:00 to source 02:00; genuine 03:xx rows must not be
blanket-shifted. ETL omissions remain unrecoverable, so the stay backbone must
be preserved with a LEFT JOIN and typed NULL endpoints.

Materialized identifier and datetime aliases are strings; cast identifiers to
INTEGER and datetime strings to `TIMESTAMP_NTZ`. Avoid offset-aware parsing and
plain `TIMESTAMP`. No new dataset-wide quirk was established and no fragment
was appended.

Reusable analysis was written to:
`mimic-iv/concepts_fhir/carryover/icustay_times/fhir-prober.md`.
