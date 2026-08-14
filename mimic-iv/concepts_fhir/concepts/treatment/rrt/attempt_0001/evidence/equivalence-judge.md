## Evidence

The independent equivalence judge returned `blocked`. It accepted the cited
upstream ETL diagnosis as intrinsic but found it essential: 372 oracle-only
rows have no served FHIR resource, changing row inclusion, while irreversible
timestamp normalization changes interval overlay and multiplicity at the
canonical RRT range join. The cited ETL sites are
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`,
`fhir_medication_administration_icu.sql:8-9,61-69`, and
`fhir_procedure_icu.sql:10-11,73-75`; original wall times are unrecoverable,
and resource ids are opaque. The unkeyed residual prevents a meaningful
representable fraction, so this is `BLOCKED_REPRESENTATION`, not an accepted
divergence.
