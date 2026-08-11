Evidence block — Demo shape gate for `height`, attempt `0002`.

Executed `uv run mimic_utils run-demo height` using embedded Pathling on Spark. All three ViewDefinitions registered and `concept.sql` executed without error. Verdict: `shape_ok`. Candidate columns exactly match the oracle: `subject_id`, `stay_id`, `charttime`, `height`; types `int`, `int`, `timestamp_ntz`, `decimal(38,2)` are compatible with `INTEGER`, `INTEGER`, `TIMESTAMP`, `DECIMAL(38,2)`. Demo row count was 69, reported only and not gated.

Artifacts: `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0002/shape.demo.json` and `candidate.demo.parquet`. No implementation artifacts were edited and no commit was made.
