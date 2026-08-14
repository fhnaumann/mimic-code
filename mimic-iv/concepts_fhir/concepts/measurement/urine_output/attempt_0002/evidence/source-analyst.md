# Source analyst evidence

Attempt `0002` reused the validated concept-level source analysis from attempt `0001`; no source SQL or DAG dependency changed. The reusable artifact is `mimic-iv/concepts_fhir/carryover/urine_output/source-analyst.md`, recorded in `carryover.json`. It specifies outputevents itemids `226559, 226560, 226561, 226584, 226563, 226564, 226565, 226567, 226557, 226558, 227488, 227489`, the `227488` positive-value negation, and grouping by `(stay_id, charttime)` with `SUM`.

This stage was reused under the carryover protocol; no new source analysis was needed and no attempt implementation artifact was modified.
