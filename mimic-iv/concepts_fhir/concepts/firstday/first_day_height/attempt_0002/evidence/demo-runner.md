**Concept:** first_day_height
**Attempt:** attempt_0002
**Verdict:** `shape_ok`

Executed `uv run mimic_utils run-demo first_day_height` with embedded Pathling on Spark successfully (exit 0, 2026-08-25 01:29:02). Registered views: `height`, `icu_encounter`, and `patient`.

The candidate returned the three manifest columns `subject_id`, `stay_id`, and `height`. The extra `patient_key` and `icu_encounter_key` columns are the manifest-declared FHIR key columns and are required for the full keyed diff; no required columns or keys were missing. Types were compatible: `subject_id` int/INTEGER, `stay_id` int/INTEGER, and `height` decimal(38,2)/DECIMAL(38,2). No incompatible types.

Demo row count was 140 (non-gating; full oracle row count is 73,181). Shape gate output: `SHAPE OK — MAY PROCEED TO FULL DATA`. This is only permission to spend an HPC run, not evidence of correctness.

Artifacts: `candidate.demo.parquet`, `shape.demo.json` in this attempt directory. No carried artifacts were edited.
