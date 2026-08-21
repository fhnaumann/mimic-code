# FHIR prober evidence

The prober read the source carryover, authoritative `MIMIC_NOTES.md`, and
relevant provisional sibling fragments, then probed the authoritative demo
Delta with embedded Pathling 9.6.0/Spark 4.0.2 and the read-only DuckDB demo
oracle.

The ICU spine maps to Encounter resources selected by the ICU identifier
system. `getResourceKey()` and `subject.getReferenceKey(Patient)` are opaque
equality keys; numeric `subject_id` and `stay_id` come from Patient/Encounter
identifier values and require integer casts. ICU `period.start` is the
`intime` anchor and must be cast directly to `TIMESTAMP_NTZ`.

The completed `vitalsign` dependency supplies opaque `icu_encounter_key` and
`patient_key`, `charttime`, and the eight consumed vital measures. The
dependency must be consumed as `FROM vitalsign`, joining its ICU encounter key
to the ICU Encounter key. The dependency's published interface does not expose
integer identifiers. Chartevents use the exact system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and the
19 active source itemids; inactive `226329` is excluded. Quantity aliases are
string-like and need numeric casts, and the served chartevents effective choice
is dateTime-only, so no native instant alias may be coalesced into it.

Demo checks found 140/140 ICU spine rows and 96,145/96,145 target Observation
rows, matching source payloads. The closed `[intime - 6 hours, intime + 1 day]`
window matched 6,067 groups, including the upper boundary. The first-day
aggregate replay matched all ordinary values and NULL patterns; temperature
mean differed only by at most `4.62e-7` floating representation. Fourteen
dependency event-key discrepancies reflect upstream chartevents DST
normalization; the source wall time is not recoverable and no resource-id
reconstruction was used. The global chartevents value-null/hard-coded tuple
exclusions affected zero selected demo rows. Missing Quantity.unit is
ancillary and unused.

Reusable mapping was written and recorded at
`mimic-iv/concepts_fhir/carryover/first_day_vitalsign/fhir-prober.md`.
The prober appended dataset-level findings to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_vitalsign.md`: served
chartevents are dateTime-only, and chartevents ETL applies global value and
hard-coded stay/time exclusions.
