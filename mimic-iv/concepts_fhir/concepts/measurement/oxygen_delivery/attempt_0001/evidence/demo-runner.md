## Evidence

Ran `uv run mimic_utils validate-demo oxygen_delivery` followed by
`uv run mimic_utils run-demo oxygen_delivery` using embedded Pathling on Spark
over the local Delta warehouse.

The implementation executed successfully and produced 1,154 rows with the
manifest's nine columns and compatible types: integer subject/stay identifiers,
timestamp_ntz charttime, float flow columns, and string device columns. The
shape gate reported `SHAPE OK` / `MAY PROCEED TO FULL DATA`. Row count was
observed only and was not used as a correctness gate.

Artifacts:

- `candidate.demo.parquet`
- `shape.demo.json`
