Evidence block — concept `acei`, stage `demo-runner`, attempt 0003.

After `mimic_utils validate-demo acei`, the embedded Pathling 9.6.0 / Spark
4.0.2 demo execution registered the four ViewDefinitions and ran
`concept.sql` successfully. It returned the expected five columns with
compatible types: `subject_id int`, `hadm_id int`, `acei string`,
`starttime timestamp_ntz`, and `stoptime timestamp_ntz`.

The candidate contained 107 demo rows. The comparator produced
`shape.demo.json` with `SHAPE OK`; the row count is recorded only as an
observation and was not used as a gate. The Parquet and shape artifacts are:

- `candidate.demo.parquet`
- `shape.demo.json`

This pass only authorizes the full-data run and is not evidence of semantic
correctness.
