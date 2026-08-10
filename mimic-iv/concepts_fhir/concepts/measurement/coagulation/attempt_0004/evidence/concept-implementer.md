Concept: coagulation, attempt_0004.

Reused both carryover analyses unchanged. Created the four ViewDefinitions and `concept.sql`, preserving exact item system/codes, comparator/text exclusions, identifier joins, left hospital Encounter join, specimen grouping, independent MAX pivots, and explicit manifest casts. The corrected SQL uses direct `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` before aggregation and final `CAST(charttime AS TIMESTAMP_NTZ)`; it contains no plain TIMESTAMP or offset-aware parsing. No unrepresentable declaration is needed and no prior artifact was edited.
