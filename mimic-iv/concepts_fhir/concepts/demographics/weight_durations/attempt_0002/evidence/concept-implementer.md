# Concept-implementer evidence

Attempt 0002 reused the source and FHIR carryover analyses and read the prior attempt plus the diagnostician's residual breakdown. It authored fresh ViewDefinitions and `concept.sql` in the new write-once attempt. The SQL retains original charttime as an intermediate and applies `ORDER BY starttime, charttime DESC` to the stay-wide `LEAD` windows and `wt_fix` first-row selection, while preserving exact codes, joins, filters, rounding, interval arithmetic, multiplicity, and `UNION ALL`. It does not attempt DST correction or resource-id inversion and explicitly casts all manifest outputs.

`uv run mimic_utils lint-sql weight_durations` passed cleanly. Artifacts are `ViewDefinition.weight_durations_observation.json`, `ViewDefinition.weight_durations_icu_encounter.json`, and `concept.sql` under attempt 0002. No unrepresentable declaration or new notes entry was needed.
