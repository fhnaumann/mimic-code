# Evidence: demo-runner (`bg`, attempt_0005)

Outcome: `shape_ok` / pass. Ran `uv run mimic_utils run-demo bg` with embedded
Pathling 9.6.0 on Spark over the demo Delta warehouse. The five ViewDefinitions
registered and `concept.sql` executed successfully, producing Parquet.

The candidate returned exactly the 27 oracle column names with no missing or
extra columns. All normalized types were compatible, including `charttime`,
`specimen`, `fio2_chartevents FLOAT`, and `aado2_calc DECIMAL(38,4)`. The demo
produced 889 rows; this is informational only and is not a correctness gate.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0005/candidate.demo.parquet/`

The shape gate explicitly permits proceeding to full data; it does not establish
correctness. No implementation artifacts or `MIMIC_NOTES.md` were modified.
