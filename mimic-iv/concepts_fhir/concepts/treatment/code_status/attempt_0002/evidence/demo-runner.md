# Demo runner evidence — code_status attempt 0002

Command: `uv run mimic_utils run-demo code_status`.

Attempt 0002 executed successfully with embedded Pathling on Spark. The four
ViewDefinitions (`cs_chart`, `cs_hosp`, `cs_icu`, `cs_patient`) registered and
the SQL completed without errors.

Shape verdict: `shape_ok`. The candidate returned exactly the eight manifest
columns (`subject_id`, `hadm_id`, `stay_id`, `charttime`, `fullcode`, `cmo`,
`dni`, `dnr`) with compatible types: seven `INTEGER` and one `TIMESTAMP`.
Demo row count was 147 and was not gated; the full oracle has 269,072 rows.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/candidate.demo.parquet/`
