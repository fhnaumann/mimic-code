## Evidence

`source-analyst` was reused from attempt 0001 via the valid carryover at
`mimic-iv/concepts_fhir/carryover/icustay_detail/source-analyst.md`.
That analysis remains valid: the source SQL is an 18-column ICU-stay-grain
projection from `icustays` joined to `admissions` and `patients`, with no
coded filters or derived dependencies, and `stay_id` is the natural key.
Original evidence: `../attempt_0001/evidence/source-analyst.md`.
