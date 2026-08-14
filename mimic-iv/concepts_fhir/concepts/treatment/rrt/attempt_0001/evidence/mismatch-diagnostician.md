## Evidence

The diagnostician read the full comparison, implementation, canonical source,
curated notes, and the named provisional leads. It found no fixable port bug.
Replay of the upstream transformations accounted for all 241 candidate-only
rows and identified 449 transformed/original-only rows; the remaining 372
oracle-only rows were absent from the served candidate. The loss is caused by
irreversible `TIMESTAMPTZ` normalization in:

- `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`
- `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`
- `mimic-fhir/sql/fhir_procedure_icu.sql:10-11,73-75`

The original wall times are not recoverable from FHIR; resource ids remain
opaque and were not used. No carryover invalidation is needed. The diagnosis
routes this `contested` review to the equivalence judge.

The diagnostician appended a dataset-wide spring-forward normalization finding
to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/rrt.md`.
