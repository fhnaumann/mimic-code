Evidence block — concept `acei`, stage `demo-runner`.

The controller transitioned attempt 0002 to VALIDATING_DEMO and
`uv run mimic_utils run-demo acei` executed the embedded Pathling 9.6.0 / Spark
4.0.2 demo path. ViewDefinitions loaded, but `concept.sql` failed before a
candidate Parquet or shape artifact was produced. Spark reported
`DATATYPE_MISSING_SIZE` at `CAST(m.drug_name AS VARCHAR)` on line 4: Spark 4
requires an explicit VARCHAR length. This is a fixable implementation bug,
not a row-count or representability result, so no HPC run was spent.

The required correction is to create a new immutable attempt using a bounded
cast such as `VARCHAR(255)`. The shared dataset note is recorded in
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`; attempt 0002 artifacts remain
unchanged.
