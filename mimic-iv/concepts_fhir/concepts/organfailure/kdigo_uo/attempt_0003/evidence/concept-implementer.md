Implemented corrected `kdigo_uo`, attempt `0003` after attempt_0002's demo Spark timeout.

Reused source/FHIR carryovers and the prior diagnosis. Reproduced the corrected SQL with explicit DOUBLE arithmetic for `TIMESTAMPDIFF` and the 3600 divisor, `COALESCE(..., CAST(1 AS DOUBLE))`, canonical rolling windows, interval/rate logic, dependency views `urine_output` and `weight_durations`, ICU Encounter identifier/key mapping, manifest casts, and opaque-id handling. No prior attempt was modified and no new dataset-wide quirk was found.

Artifacts produced:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0003/ViewDefinition.icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0003/concept.sql`

Verification: `uv run mimic_utils lint-sql kdigo_uo` reported clean.
