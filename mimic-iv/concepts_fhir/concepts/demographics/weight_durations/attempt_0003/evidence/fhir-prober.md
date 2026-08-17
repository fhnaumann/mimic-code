# FHIR-prober evidence

The prober reran the invalidated stage with the canonical source SQL, source
carryover, curated `MIMIC_NOTES.md`, relevant provisional fragments, prior
diagnostics, the FHIR mapping skill, embedded Pathling 9.6.0/Spark 4.0.2 over
the authoritative demo Delta, and the read-only demo oracle. It updated and
recorded the reusable mapping at
`mimic-iv/concepts_fhir/carryover/weight_durations/fhir-prober.md`.

It mapped ICU chartevents to `Observation` and ICU stays to `Encounter`.
Observation coding uses the exact system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` with
codes `226512` and `224639`; the source/FHIR counts were 129/129 and 441/441,
570/570 total. Observation encounter references joined ICU Encounter resource
keys by opaque equality; ICU `stay_id` came from the ICU identifier value and
not from a resource UUID. DateTime and period aliases were strings, instant was
native Spark timestamp, and Quantity value was a string alias over decimal
`(32,6)`, requiring casts before arithmetic. ICU Encounter identifiers and
period endpoints were populated for 140/140 resources. Canonical interval
replay matched the demo full-tuple multiset 578/578.

The global chartevents omission predicates were checked: all 570 target source
values were non-null and the hard-coded exclusion tuple had zero rows. The
prober re-confirmed that ICU Encounter period endpoints and chartevent times
can be irreversibly DST-normalized upstream; attempt 0002's full diagnosis
found eight chartevent/`LEAD` residuals and nine ICU-intime arithmetic
residuals. It did not parse or regenerate any resource id. No new
dataset-wide finding was appended; `MIMIC_NOTES.md` was not edited.

Evidence and mapping artifacts:

- `mimic-iv/concepts_fhir/carryover/weight_durations/fhir-prober.md`
- `mimic-iv/concepts_fhir/concepts/demographics/weight_durations/attempt_0003/evidence/fhir-prober.md`
