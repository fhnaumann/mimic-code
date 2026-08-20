# Source analyst evidence — `first_day_height`

Read the canonical SQL at `mimic-iv/concepts/firstday/first_day_height.sql`,
the DAG and oracle manifest entries, `AGENTS.md`, curated `MIMIC_NOTES.md`,
and the relevant `height`, `weight_durations`, and `icustay_times` fragment
leads. The SQL SHA256 matched the DAG.

`first_day_height` is a level-1 concept depending on `height`. It consumes the
completed dependency view as `height`, left-joining it to every ICU stay on
`stay_id` and inclusive `charttime` bounds `[intime - 6 hours, intime + 1 day]`.
It groups by `subject_id, stay_id` and emits `ROUND(CAST(AVG(height) AS NUMERIC),
2)`. The manifest shape is `subject_id INTEGER`, `stay_id INTEGER`, and
`height DECIMAL(38,2)`, with `stay_id` as the empirical comparison key and
`patient_key`/`icu_encounter_key` as required opaque FHIR identity outputs.

The target SQL has no direct coded filter. Its dependency preserves source
itemids `226707` and `226730`, converts inches/centimetres and applies the
dependency's strict plausibility bounds. The dependency boundary must not be
inlined or rederived. Essential inputs are ICU identifiers, `intime`,
dependency `stay_id`, `charttime`, and `height`; time normalization can affect
window membership and the average. Resource/reference ids remain opaque and
may only support equality joins.

No new dataset-wide quirk was identified by this stage, so no notes fragment
was appended. Carryover was recorded at
`mimic-iv/concepts_fhir/carryover/first_day_height/source-analyst.md`.
