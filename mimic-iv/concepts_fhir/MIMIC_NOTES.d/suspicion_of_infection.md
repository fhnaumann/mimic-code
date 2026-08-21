## Microbiology Specimen.identifier carries the relational micro_specimen_id
- Affected: `Specimen.identifier` on the microbiology specimen stream and `Observation.specimen` joins for `mimic-observation-micro-test`
- Verified: `suspicion_of_infection` authoritative demo Delta probe with embedded Pathling 9.6.0/Spark 4.0.2 found 1,336/1,336 targeted Specimen resources with `identifier.system=http://mimic.mit.edu/fhir/mimic/identifier/specimen-micro` and a non-null identifier value; the values joined the 1,893 micro-test `(specimen,test)` groups to the DuckDB `micro_specimen_id` groups exactly (1,893/1,893). The resource/reference keys were used only for equality joins.

## Microbiology date-only cultures are identified by absent Specimen.collection.collectedDateTime
- Affected: `Specimen.collection.collectedDateTime` and `Observation.effectiveDateTime` on the microbiology test stream
- Verified: `suspicion_of_infection` source/FHIR probe found 45/1,336 source specimen groups with `MAX(charttime) IS NULL` and 45/1,336 targeted FHIR Specimens with null `collection.collectedDateTime`; all 1,893 micro-test effective values were populated and the date-only test-group effective timestamps matched `MAX(COALESCE(charttime, chartdate))` exactly (1,893/1,893). Use the surviving collection-null discriminator for the date-only branch; do not infer it from a resource id.
