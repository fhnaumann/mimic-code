Evidence block — phenylephrine demo shape gate

`uv run mimic_utils run-demo phenylephrine` executed successfully with embedded Pathling on Spark. The shape verdict was `shape_ok`; candidate and oracle column names matched exactly: `stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`. Types were compatible (`INTEGER`, `FLOAT`, and timestamp). Demo row count was 625 and was treated as non-gating evidence only; the full oracle count is 193,260.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` under `mimic-iv/concepts_fhir/concepts/medication/phenylephrine/attempt_0001/`. No implementation artifacts were modified and no commit was made.
