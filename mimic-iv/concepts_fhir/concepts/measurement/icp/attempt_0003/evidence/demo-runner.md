Evidence block

`uv run mimic_utils validate-demo icp` transitioned the concept to
`VALIDATING_DEMO` after SQL lint passed. Embedded Pathling on Spark 4.0.2 ran
the three ViewDefinitions and `concept.sql` over the demo Delta warehouse.

Result: 303 rows (reported, not gated); columns and compatible types were
`subject_id int`, `stay_id int`, `charttime timestamp_ntz`, and `icp float`.
The shape gate was `SHAPE OK`; the attempt may proceed to full-data validation.
Zero new dataset-wide quirks were found.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json`
