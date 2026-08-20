# Mismatch-diagnostician evidence — neuroblock attempt 0005

The diagnosed `review` is intrinsic upstream representation loss, not a port
bug. `mimic-fhir/sql/fhir_medication_administration_icu.sql:20` places
`ie.orderid` only inside `uuid_generate_v5(...)`; lines 40 and 44 write that
value as the opaque resource id, while the exhaustive resource construction at
lines 42–101 has no `identifier`, `request`, or other queryable orderid field.
The orderid integer is therefore unrecoverable by any compliant query, and
resource-id inversion is forbidden.

The candidate's exact item/code and rate filters match the canonical SQL. The
full result has schema match and a VOID DIFF: 14,174 `only_oracle` and 14,174
`only_candidate` rows arise solely because declared-unrepresentable `orderid`
is the manifest key; they do not establish invented rows or fan-out. The
diagnosis found no carryover stage to invalidate.

The missing value is ancillary to the clinical grain: canonical SQL does not
use orderid for inclusion, grouping, aggregation, temporal logic, or a derived
clinical value, and the supplied full-oracle measurement found
`(stay_id,starttime,endtime)` unique across all 14,174 rows. The diagnostician
did not make a terminal decision; the equivalence judge must decide.

Relevant sibling fragments were treated as provisional leads only. No new
dataset-wide fragment was appended.

Evidence checked: `comparison.full.json`, all attempt-0005 implementation
artifacts, neuroblock carryover, canonical source SQL, manifest lines
2970–3007, `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, and the cited
upstream ETL file.
