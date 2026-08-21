# Full-data contested diagnosis

The diagnostician found no target semantic bug. Candidate SQL matches the
canonical five-rate predicate, coefficients, COALESCE behavior, and four-place
rounding; it adds no grouping, deduplication, windows, or target-side temporal
construction. The ICU Encounter join is one-to-one and only restores `stay_id`
from the identifier associated with the opaque dependency key.

The `+20` row delta and unkeyed residuals are inherited from the accepted
`vasoactive_agent` divergence. Its interval grid uses `UNION DISTINCT`,
`LEAD`, and seven containment joins, so upstream shifted administration
endpoints propagate through interval construction. The cited upstream causes
are `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`
(`TIMESTAMPTZ` endpoint normalization), `:12-15,85-99` (six-decimal Quantity
serialization), and `:7-23,38-100` (omitted `patientweight`). The target
inherits one ancillary phenylephrine patientweight NULL; it does not use
linkorderid.

Full result: oracle 619,330, candidate 619,350 (+20, 0.00323%); residual
1,843 only-oracle and 1,863 only-candidate (unkeyed, no pairing); exact
multiset intersection 617,487 (99.70242% of oracle). Column-drift indicators
were dose 2,442, starttime 162, endtime 164, and stay_id 24, overlapping rather
than additive. Residual attributable to a target defect: zero. The original
wall time, low-order precision, and patientweight are absent from permissible
FHIR elements; opaque ids cannot be used to recover them. Proven DST loss is
excluded from essential-loss blocking, and the inherited patientweight gap is
ancillary here.

Recommendation: do not retry; proceed to the equivalence judge with the
diagnosis and ETL citations verbatim. No carryover invalidation or notes
fragment append was needed. The diagnostician read curated notes only; the
orchestrator supplied sibling fragments as provisional leads and they were not
cited.

Artifacts read: attempt comparison/run metadata, candidate SQL/ViewDefinition,
canonical target and dependency SQL, manifest, completed dependency evidence,
curated notes, and upstream ETL SQL. No attempt artifact was modified.
