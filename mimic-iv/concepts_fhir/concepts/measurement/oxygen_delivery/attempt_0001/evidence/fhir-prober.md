## Evidence

Read `MIMIC_NOTES.md`, the existing notes fragments, source analysis, oracle
manifest, and the canonical Observation ViewDefinition reference. Probed the
authoritative demo Delta with embedded Pathling.

Mapped the four exact chartevents codes (`223834`, `227582`, `227287`,
`226732`) under the chartevents code system. Patient and ICU Encounter
identifiers are obtained through opaque reference-key equality joins and
identifier values; `effective.dateTime` maps to charttime and `issued` maps to
storetime. Quantity value supplies flow values; `valueString` supplies device
labels. Demo source/FHIR tuples and storetimes agreed 4,393/4,393, and the
pivot agreed 1,154/1,154 groups. Ranking retains source semantics and does not
include stay_id in partitions, joins, or grouping. Charttime DST normalization
is potentially essential because it can alter the natural key and aggregation;
resource ids must not be used to recover it.

The reusable mapping is in
`mimic-iv/concepts_fhir/carryover/oxygen_delivery/fhir-prober.md`, and the
dataset-wide findings recorded for this goal are in
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/oxygen_delivery.md`.
