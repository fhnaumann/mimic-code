# FHIR-prober evidence (reused carryover)

The existing `apsiii` FHIR mapping was reused for attempt 0002 under the resume
plan. It maps the ICU and hospital Encounter identifier/key spine, Patient
identifier/key, hospital-linked Condition coding, and the six completed
dependency views. It confirms the served proprietary ICD coding systems and
the literal CKD prefixes, and records the prior dependency observations and
GCS representability lead. It forbids resource-id inference and preserves the
dependency boundary.

Reusable artifact: `mimic-iv/concepts_fhir/carryover/apsiii/fhir-prober.md`.
No new probe was spawned and no implementation artifact was authored by this
stage. The current dependency states were checked separately: all six are
completed, with `first_day_gcs` attempt 0003 completed exactly after the
upstream GCS representation fix.
