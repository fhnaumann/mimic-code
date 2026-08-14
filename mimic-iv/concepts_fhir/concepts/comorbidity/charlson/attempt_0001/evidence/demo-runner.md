# Demo-runner evidence — charlson attempt 0001

The embedded Pathling/Spark demo shape gate had already run once before the
runner resumed; the write-once guard correctly refused a second execution
because `candidate.demo.parquet` existed. The recorded result is `shape_ok`:
execution succeeded, all 21 expected column names matched, no columns were
missing or extra, and all 21 candidate Spark `int` types were compatible with
the manifest INTEGER types. The 275 demo rows are observational only and were
not used as a correctness gate; the run was not an unsure zero-row case.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0001/shape.demo.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0001/candidate.demo.parquet/`

State remained `VALIDATING_DEMO`; no implementation or notes artifact was
changed by the refused rerun.
