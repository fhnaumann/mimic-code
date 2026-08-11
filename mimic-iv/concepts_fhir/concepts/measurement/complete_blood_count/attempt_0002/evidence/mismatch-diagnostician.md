# Mismatch-diagnostician evidence — complete_blood_count, attempt_0002

The 204 `charttime` conflicts are upstream transformation loss, not a port bug.
The port correctly preserves the served Observation effective wall-clock text
with `TIMESTAMP_NTZ` and performs the canonical specimen-level MAX. The exact
upstream citation is `mimic-fhir/sql/fhir_observation_labevents.sql:15`, which
casts naive `lab.charttime` through `TIMESTAMPTZ`, and line 121, which writes the
transformed value as `Observation.effectiveDateTime`. Spring-forward-gap 02:xx
times are normalized to 03:xx, matching every observed conflict. The linked
Specimen repeats the transformation at `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58`.

The original wall-clock value is non-injectively lost; Observation identifiers
carry only labevent_id, and subtracting an hour would corrupt genuine 03:xx
values. No carryover stage is implicated, so no invalidation or retry is needed.
No new notes fragment entry was added because the quirk is already recorded in
the curated notes and CBC fragment.

This citation and conclusion must be passed verbatim to the equivalence judge.
