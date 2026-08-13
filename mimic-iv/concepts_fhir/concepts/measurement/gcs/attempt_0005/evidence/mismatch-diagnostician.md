# Mismatch diagnostician evidence — gcs

The full-data result is a `review` at the `contested` tier, not a mechanical
mismatch. The diagnosis is upstream representation loss, not a fixable port
bug.

`mimic-fhir/sql/fhir_observation_chartevents.sql:69-80` writes numeric
`valueQuantity` when `valuenum` is present and does not retain the source text.
Thus `No Response-ETT` and `No Response` are both served as Quantity 1. The
source SQL's sentinel controls `gcs`, `gcs_verbal`, `gcs_unable`, and the
six-hour carry-forward, so the missing discriminator is essential and cannot
be replaced by a typed NULL or a Quantity-1 heuristic. It is unrecoverable
from direct FHIR values without forbidden resource-ID inversion.

The comparison reports 576,086 conflicts across `gcs`, `gcs_verbal`, and
`gcs_unable`; this is the expected semantic effect of the lost sentinel. The
effective-time `TIMESTAMPTZ` normalization in
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` explains 74 re-paired
candidate/oracle keys and the remaining 24 oracle-only collision residuals;
historical UUID recovery is forbidden and was not used.

Recommendation to the equivalence judge: `blocked` under the essential-loss
rule, because publishing this partial table would conceal unreliable core GCS
values and carry-forward semantics. No carryover stage is at fault and no
retry is recommended.

Files checked included `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the canonical GCS
SQL, attempt-0005 comparison, implementation and stage evidence, GCS
carryover, relevant attempt history, and the upstream chartevents ETL. No
fragment was read or appended. This evidence was written once at this path.
