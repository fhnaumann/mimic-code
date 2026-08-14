## Evidence

The independent equivalence judge returned `accept` for the contested review.
Raw full-oracle replay reproduced 2,827,715 rows exactly; replaying all cited
upstream TIMESTAMPTZ casts reproduced the candidate exactly at 2,827,507 rows,
with 449 `only_oracle` and 241 `only_candidate` residual multiset entries and
zero unexplained residual.  The provenance is
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` for 608 shifted chart
times and `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`
for 27 shifted interval endpoints; the analogous procedure cast is
`mimic-fhir/sql/fhir_procedure_icu.sql:10-11,73-75`, with no selected procedure
endpoint moved.

The judge confirmed propagation through `rrt.sql:296-326`, semantic FHIR
unrecoverability of the original DST-gap wall times, the annual-gap rarity,
and the prohibition on opaque resource-ID recovery.  It also confirmed that
attempt 0003 includes the previously omitted `225965` code.  With no key,
`classification=unavailable_no_key` and `attributed=[]` honestly indicate that
mechanical comparator attribution was unavailable; the diagnostician's exact
source-side replay closes the proof.  No divergent dependencies were present.
