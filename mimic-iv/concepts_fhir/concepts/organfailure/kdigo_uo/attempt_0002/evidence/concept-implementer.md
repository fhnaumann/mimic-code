Implemented corrected `kdigo_uo`, attempt `0002`.

Reused the recorded source and FHIR carryovers and read attempt_0001's diagnosis. Applied the exact fix: cast `TIMESTAMPDIFF(SECOND, previous_charttime, charttime)` to `DOUBLE`, divide by `CAST(3600 AS DOUBLE)`, and use `COALESCE(..., CAST(1 AS DOUBLE))`. Preserved the ICU Encounter projection with opaque encounter/patient keys, the `urine_output` and `weight_durations` dependency views, canonical rolling windows, interval join, output casts, and all resource-id rules. No new dataset-wide quirk was found and no notes fragment was appended.

Artifacts produced:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0002/ViewDefinition.icu_encounter.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0002/concept.sql`

Verification: `uv run mimic_utils lint-sql kdigo_uo` reported clean.
