# Mismatch-diagnostician evidence (reused prior diagnosis)

The comparator set `diagnostician_required: true` for the 17 residual conflict
rows, but a complete diagnosis already exists for the same full-data result in
attempt 0002. Attempt 0003 changes the prior implementation only by adding
the required opaque `icu_encounter_key`/`patient_key` output columns and
explicit ICU identifier-system selection; its compared five-column output and
full comparator counts are identical to attempt 0002. The prior diagnosis was
therefore reused rather than spawning a duplicate diagnosis.

The reusable diagnosis is
`attempt_0002/evidence/mismatch-diagnostician.md`. It closes all 17 residuals
by full source-side replay: nine ICU-intime arithmetic effects cite
`mimic-fhir/sql/fhir_encounter_icu.sql:31-32,97-100`, and eight chartevents
window/LEAD effects cite `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`.
It also establishes that all 38 `only_oracle` and 32 `only_candidate` rows are
the same upstream DST-shifted events, with six key collisions propagated by
the concept's `LEAD`/`UNION ALL` semantics. The original wall times are absent
from FHIR and opaque resource ids were not used for recovery.

There are no divergent dependencies (`ConversionController.divergent_dependencies`
returned `[]`). The prior judge evidence and diagnosis are supplied to the
current judge; no attempt artifact was modified.
