Concept: coagulation, attempt_0003.

Reused source-analyst and fhir-prober carryovers unchanged. Created the four ViewDefinitions and `concept.sql` with the prior exact lab mappings, comparator/text exclusions, identifier-spine joins, left hospital Encounter join, specimen grouping, independent MAX pivots, and manifest-typed casts. Corrected charttime by using `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` before specimen-level MAX; no native timestamp is mixed into the expression and no offset-aware parsing is used. No unrepresentable declaration is needed and no old artifact was edited.
