## Evidence

- Concept: dobutamine
- Attempt: attempt_0004 (replay/data rebuild)
- Stage: demo-runner
- Read/checks: Ran `uv run mimic_utils run-demo dobutamine` using embedded Pathling on Spark and inspected `shape.demo.json` against the oracle manifest.
- Result: `shape_ok`; execution succeeded. All six oracle columns are present (`stay_id`, `linkorderid`, `vaso_rate`, `vaso_amount`, `starttime`, `endtime`) with compatible types. The two extra columns (`patient_key`, `icu_encounter_key`) are required manifest key columns, not unexpected output. Demo row count was 44 and is non-gating.
- Artifacts: `candidate.demo.parquet`, `shape.demo.json` in this attempt directory.
- Dataset-wide quirk check: no new quirk; existing dobutamine fragment entries on absent ICU inputevent identifiers, conditional effective[x], and decimal(32,6) quantities remain applicable.
