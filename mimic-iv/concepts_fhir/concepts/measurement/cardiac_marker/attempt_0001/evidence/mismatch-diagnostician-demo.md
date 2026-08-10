## Mismatch-diagnostician evidence

The demo failure is a fixable, attempt-scoped SQL syntax bug, not a mapping or carryover problem. In `attempt_0001/concept.sql:42-45`, the single-quoted Spark pattern `'yyyy-MM-dd''T''HH:mm:ssXXX'` evaluates without literal quotes around `T`, so Spark raises `Unknown pattern letter: T` during Parquet evaluation.

The smallest immutable fix is to create a new attempt and use the double-quoted SQL string `"yyyy-MM-dd'T'HH:mm:ssXXX"` for the fallback `TRY_TO_TIMESTAMP` pattern. Neither `source-analyst` nor `fhir-prober` carryover is implicated or should be invalidated. No dataset-wide quirk was discovered.

Recommended controller procedure: fail attempt 1 with the engineering error, retry to create attempt 2, reuse both carryover stages, reproduce the ViewDefinitions unchanged, and author corrected `concept.sql` before rerunning the demo gate.
