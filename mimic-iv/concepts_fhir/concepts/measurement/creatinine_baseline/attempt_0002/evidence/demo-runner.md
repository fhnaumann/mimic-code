Evidence block

Concept: `creatinine_baseline`, attempt `0002`.

The demo shape gate executed successfully with embedded Pathling 9.6.0 on Spark over the local demo Delta warehouse. The artifact verdict is `shape_ok` and permits proceeding to full data.

All seven candidate columns matched the oracle manifest in order: `hadm_id, gender, age, scr_min, ckd, mdrd_est, scr_baseline`. Candidate types were compatible: `int, string, bigint, double, int, double, double` versus `INTEGER, VARCHAR, BIGINT, DOUBLE, INTEGER, DOUBLE, DOUBLE`. No execution, column-name, or type errors occurred. The reported 275 candidate rows versus 431231 oracle rows is observation only and was not gated.

Artifacts:
- `candidate.demo.parquet`
- `shape.demo.json` (`format_version` 2.0, verdict `shape_ok`)
