Evidence block — code_status, attempt 0004

The independent equivalence judge read the loop contract, curated MIMIC_NOTES,
canonical code_status SQL, attempt 0004 comparison and implementation, the
diagnostician evidence, prior attempt artifacts, and cited upstream ETL SQL.

Verdict: BLOCKED. The unkeyed full-tuple comparison is contested with 4
only_candidate and 197,935 only_oracle residual tuples; residual pairing is
unavailable. Four residuals are attributable to irrecoverable DST normalization
from `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, leaving 197,931
missing General Care/Code-status POE rows. The canonical branch is
`mimic-iv/concepts/treatment/code_status.sql:36-77`; the served FHIR ETL only
emits medication/IV/TPN POE subsets and omits `poe_detail.field_value`
(`mimic-fhir/sql/fhir_medication_request.sql:188-205,250-288`), with no separate
code-status transform. The loss changes row inclusion, event time,
multiplicity, ICU association, and status outputs, so it is essential rather
than an ancillary gap.

Fidelity evidence: 71,141 represented chart rows / 269,072 oracle rows ≈
26.44%; 197,931 essential POE rows missing ≈ 73.56%. Formal identical and
representable fractions are unavailable because the concept has no natural key
and residual pairing failed. The previous hardcoded/reconstructed resource-ID
recovery is inadmissible; the current attempt uses ids only for opaque equality
joins. No carryover stage was invalidated, no divergent dependencies exist, and
no further full run is warranted.

The judge confirmed the dataset-wide POE omission finding in the owned notes
fragment, but terminal promotion is not performed for a blocked outcome.
