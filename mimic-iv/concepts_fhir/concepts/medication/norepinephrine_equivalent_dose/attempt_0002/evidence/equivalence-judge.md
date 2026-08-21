# Equivalence judge evidence

**Verdict: accept.** The contested divergence is wholly inherited from
judge-accepted `vasoactive_agent`; attempt_0002 adds no independent mapping,
filter, formula, join, fan-out, or cast defect. It exactly consumes the
completed dependency, applies the canonical five-rate predicate and four-place
formula, and uses a one-to-one ICU Encounter identifier join only to restore
`stay_id`.

The judge confirmed upstream provenance and unrecoverability:

- `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69` casts
  administration endpoints through `TIMESTAMPTZ` and writes only normalized
  effective values; original wall times are absent from FHIR.
- `:12-15,85-99` serializes dose/rate Quantities at served six-decimal
  precision; discarded low-order precision is unrecoverable.
- `:7-23,38-100` does not serialize `inputevents.patientweight`; the inherited
  phenylephrine NULL cannot be recovered by a FHIR query.

The 112 shifted administrations among 614,600 dependency rows (0.0182%)
propagate through `mimic-iv/concepts/medication/vasoactive_agent.sql:9-80,96-127`
(`UNION DISTINCT`, `LEAD`, containment) and produce the target +20/619,330
row delta (0.00323%). The full unkeyed residual was 1,843 only-oracle and
1,863 only-candidate, with no pairing; these are alignment artifacts rather
than affected-row counts. Exact multiset intersection was 617,487 rows
(99.70242% of oracle); identical/representable fractions are unavailable.

No target-originated essential loss exists. Proven DST loss is exempt from
blocking, and the inherited patientweight gap is ancillary to this target.
The divergent dependency list is `['vasoactive_agent']`. No notes fragment was
read or appended by the judge; no files were modified.

Artifact: this judge evidence file. The cited comparison and run metadata are
in attempt_0002.
