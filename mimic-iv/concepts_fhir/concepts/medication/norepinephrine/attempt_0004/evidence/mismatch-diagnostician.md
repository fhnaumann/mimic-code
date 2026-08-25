# Mismatch diagnosis

The attempt_0004 `review` is a VOID-DIFF alignment artifact, not a port defect.
The manifest key `(linkorderid, starttime)` contains the declared-unrepresentable
`linkorderid`; all 336,000 oracle rows have it while every candidate row emits
typed NULL, so the symmetric 336,000 `only_oracle` / `only_candidate` counts do
not measure fidelity. There are zero `differing_conflict` and zero
`differing_null_only` rows.

The canonical query is a direct filtered projection of `inputevents` with no
join, grouping, aggregation, or `DISTINCT` (`mimic-iv/concepts/medication/norepinephrine.sql:3-16`);
`linkorderid` is only projected. The ETL creates one MedicationAdministration
per inputevent and does not serialize `linkorderid` or an identifier
(`mimic-fhir/sql/fhir_medication_administration_icu.sql:1,7-23,24-35,38-100`).
The source `orderid` appears only in the opaque UUID at line 20 and cannot be
inverted. A focused representable multiset comparison found 336,000 rows on
both sides with zero differences, confirming row multiplicity and timing
tuples are preserved.

No actual timing residual remains after the UTC rebuild: attempt_0003 had 58
oracle-only and 58 candidate-only timing tuples, while attempt_0004 had 0/0.
The comparator's key-attribution residual is caused by the NULL key and is not
evidence of a remaining DST issue. No retry or carryover invalidation is
warranted.

Evidence read: `comparison.full.json`, `replay_provenance.json`, attempt_0003
comparison and diagnosis/judge evidence, canonical SQL, ViewDefinitions,
`unrepresentable.json`, `MIMIC_NOTES.md`, relevant provisional medication
fragments, and `mimic-fhir/sql/fhir_medication_administration_icu.sql`.
