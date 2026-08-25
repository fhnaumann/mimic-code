## Evidence

The replayed `kdigo_uo` attempt 0005 ran `uv run mimic_utils run-demo kdigo_uo`
from the repository root. Embedded Pathling on Spark executed the ViewDefinitions
and SQL successfully. The shape verdict was `shape_ok`; all 12 oracle columns
were present, the declared `icu_encounter_key` and `patient_key` output columns
were accepted as manifest key columns, and no incompatible types were found.
The demo produced 7,317 rows; row count was observed only and was not gated.

Artifacts: `candidate.demo.parquet` and `shape.demo.json` in this attempt.
