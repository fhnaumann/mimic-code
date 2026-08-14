# Equivalence-judge evidence — charlson attempt 0001

The independent judge returned **accept** for the contested review. It
confirmed 431,170/431,231 identical rows (99.9859%), with 61 conflicts only in
`age_score` and `charlson_comorbidity_index`, and zero only-oracle,
only-candidate, or null-only rows. The accepted cause is inherited from the
divergent `age` dependency: `mimic-fhir/sql/fhir_patient.sql:15` synthesizes
`Patient.birthDate` from `MIN(transfers.intime) - anchor_age` (written at line
108), while canonical age needs `anchor_age` and `anchor_year` at
`mimic-iv/concepts/demographics/age.sql:30`. No FHIR element or extension
carries the anchor pair, so the oracle age is unrecoverable by a defensible
FHIR query. The candidate's diagnosis flags, identifiers, thresholds, and
arithmetic match; the 61 clinically meaningful score differences are
downstream propagation of the already accepted upstream age transformation.

Judge verdict: `accept`. No new dataset-wide quirk was identified and no
notes fragment was changed.
