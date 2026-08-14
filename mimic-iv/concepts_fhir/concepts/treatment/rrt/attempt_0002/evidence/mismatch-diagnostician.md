## Evidence

The diagnostician found two independent causes in the contested review.  A
full-oracle source replay attributed 449 of 821 `only_oracle` rows and all 241
`only_candidate` rows to 635 selected source records moved by upstream
TIMESTAMPTZ casts: 608 chartevents rows through
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` and 27 inputevents
intervals through `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-67`.
The concept's `UNION DISTINCT` and inclusive range overlay propagate those
shifts, so the output counts are not additive.  The original wall times are
not recoverable from semantic FHIR elements; resource ids were not used.

The remaining 372 `only_oracle` rows are a fixable implementation bug: code
`225965` is missing from the attempt 0002 chartevents ViewDefinition filter and
outer SQL filter, despite its existing active/type CASE logic and the
canonical source filter.  Full-oracle evidence found 2,706 selected source
rows and 332 unique `stg0` contributions, whose range overlay expands to the
372 missing outputs.  The recommended fix is to add `225965` to both filters;
no carryover stage is implicated.

Relevant diagnosis artifacts and citations:
- `comparison.full.json`
- `mimic-iv/concepts/treatment/rrt.sql:99-100,133-158,163-225`
- `mimic-fhir/sql/fhir_observation_chartevents.sql:9,58-63,67,77-80`
- `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-67`
