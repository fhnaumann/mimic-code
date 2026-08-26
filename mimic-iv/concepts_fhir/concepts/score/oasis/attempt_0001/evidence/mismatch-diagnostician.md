# Mismatch-diagnostician evidence

Concept: `oasis`; attempt: `0001`.

The diagnostician read the full comparison, run metadata, immutable attempt
SQL/ViewDefinitions, canonical OASIS SQL, completed dependency interfaces,
the oracle manifest, curated `MIMIC_NOTES.md`, and the owned fragment leads.
The result is not judge-ready because the attempt contains two fixable
implementation defects plus a residual upstream representation loss.

The 3,349 elective-related conflicts were caused primarily by the attempt's
`Encounter.class='AMB'` heuristic. Upstream `mimic-fhir/sql/fhir_etl/map_encounter_class.sql:13-15`
collapses several admission types, but
`mimic-fhir/sql/fhir_etl/map_encounter_priority.sql:12-20`, written by
`mimic-fhir/sql/fhir_encounter.sql:93-96,135-141`, preserves elective status as
priority code `EL`; the ViewDefinition omitted that field. Full-data
decomposition found 3,295 heuristic false positives and 54 false negatives.
The fix is to project/filter the exact priority code `EL`.

The remaining 54 elective false negatives are intrinsic: the ETL ranks source
services by `transfertime`, keeps only the first row, and writes one current
service. The relevant citations are
`mimic-fhir/sql/fhir_encounter.sql:45-57,71,142-147`; later surgical services
before the OASIS cutoff and their times are absent from FHIR. This loss
changes `electivesurgery`, its score, total OASIS, and probability, so it is
essential evidence for the judge after the fixable defect is removed.

The 373 `preiculos` conflicts are a separate SQL dialect bug. The attempt uses
`TIMESTAMPDIFF(MINUTE, ...)`, which truncates negative elapsed units toward
zero, while canonical `DATETIME_DIFF(..., MINUTE)` counts minute boundaries.
Every conflict is negative and candidate is exactly oracle + 1 minute (for
example -142/-143 and -60/-61). The timestamp mappings themselves are exact
under the rebuilt UTC warehouse; use minute-truncated operands before
`TIMESTAMPDIFF` or equivalent boundary semantics.

Diagnosis requires a new immutable attempt. `fhir-prober` carryover is
invalidated because its mapping missed the served priority discriminator;
source analysis remains reusable. No implementation artifacts, state, or
commit were changed by this stage. The diagnostician appended its dataset-wide
priority/service-history finding to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/oasis.md`.
