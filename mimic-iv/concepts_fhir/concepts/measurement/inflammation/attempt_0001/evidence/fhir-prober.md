# FHIR prober evidence

Concept `inflammation`, attempt `0001`.

Embedded Pathling 9.6.0/Spark 4.0.2 probing over the authoritative demo Delta
mapped labevents itemid `50889` to `Observation.code.coding` with system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` and code `50889`.
The qualifying FHIR value is `(value).ofType(Quantity).value`, materialized as
a string and requiring a `DOUBLE` cast; comparator-bearing synthesized values
and `valueString` rows must be excluded. Effective time is
`(effective).ofType(dateTime)` and must be parsed as `TIMESTAMP_NTZ`.

The specimen spine is
`specimen.getReferenceKey(Specimen)` joined to
`Specimen.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value`.
Subject and hospital encounter identifiers similarly come from linked Patient
and Encounter `identifier.value` strings, cast to integers. Encounter linkage
is incomplete and therefore requires a left join.

Probe counts: 44 target coding/resources, 42 positive non-null numeric source
rows and qualifying FHIR rows, 42 specimen groups, 44 effective dateTimes,
44 subjects/specimens, and 26 encounter references. The 2 remaining resources
were valueString rows corresponding to NULL relational `valuenum`.

No new dataset-wide quirk was found; no `MIMIC_NOTES.d/inflammation.md`
fragment was appended. Reusable mapping was written to and recorded from:
`mimic-iv/concepts_fhir/carryover/inflammation/fhir-prober.md`.
