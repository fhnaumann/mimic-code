# Source-analyst evidence — sirs, attempt_0001

The source analyst read `mimic-iv/concepts/score/sirs.sql`, the SIRS DAG entry,
and the relevant curated/provisional MIMIC notes. It verified the three
completed dependency boundaries (`first_day_bg_art`, `first_day_lab`, and
`first_day_vitalsign`), the ICU `stay_id` left-join spine, the no-filter
behavior, the four ordered NULL-aware score branches, the final NULL-to-zero
sum, and the one-row-per-stay intended grain. No coded literals or raw FHIR
mapping is part of SIRS itself; dependency stems must remain unqualified in
candidate SQL. Resource/reference identifiers remain opaque.

Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/sirs/source-analyst.md` and recorded with
`mimic_utils carryover-record sirs --stage source-analyst`.
