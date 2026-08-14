# Source analyst evidence

Concept: `urine_output`.

Read the canonical SQL, DAG, LOOP_CONTRACT, MIMIC_NOTES, relevant schemas, and notes protocol. The sole table is `mimiciv_icu.outputevents`; columns are `stay_id INTEGER`, `charttime TIMESTAMP`, `itemid INTEGER`, and `value FLOAT`. The filter includes exact itemids `226559, 226560, 226561, 226584, 226563, 226564, 226565, 226567, 226557, 226558, 227488, 227489`; item `227488` with positive value is negated. There are no joins, time windows, derived dependencies, or other filters. Output is grouped by `(stay_id, charttime)` with `SUM(urineoutput)`, producing `stay_id`, `charttime`, and `urineoutput DOUBLE`. The provisional FHIR coding system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`.

Carryover written to `mimic-iv/concepts_fhir/carryover/urine_output/source-analyst.md` and recorded via `uv run mimic_utils carryover-record urine_output --stage source-analyst`. No attempt artifacts were modified and no commit was made.

Dataset-wide quirk lead: ICU output events are itemid-derived Observations and may require opaque resource identity only for joins; the source itemid must be filtered by the exact `mimic-d-items` system and code.

Artifacts:
- `mimic-iv/concepts_fhir/carryover/urine_output/source-analyst.md`
- `mimic-iv/concepts_fhir/carryover/urine_output/carryover.json`
