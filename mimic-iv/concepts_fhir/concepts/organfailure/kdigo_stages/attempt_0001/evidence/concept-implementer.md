Evidence block

Concept: `kdigo_stages`; attempt: `0001`.

Produced:
- `ViewDefinition.kdigo_stages_icu_encounter.json`
- `ViewDefinition.kdigo_stages_patient.json`
- `ViewDefinition.kdigo_stages_hospital_encounter.json`
- `concept.sql`

The SQL preserves ICU encounter spine, opaque-key joins, identifier casts, NULL-preserving joins, `UNION DISTINCT` event axis, KDIGO stage CASE logic, `GREATEST`/`COALESCE`, and subject-level six-hour `RANGE` smoothing. It consumes only `kdigo_creatinine`, `kdigo_uo`, and `crrt` dependency views.

Read and applied `MIMIC_NOTES.md`, including identifier/key, opaque-resource-id, encounter-system, Spark cast, and `TIMESTAMP_NTZ` datetime guidance. Read relevant fragments: `README.md`, `crrt.md`, `kdigo_creatinine.md`, `kdigo_uo.md`, `urine_output.md`, `first_day_urine_output.md`, `weight_durations.md`, `first_day_weight.md`, `icustay_times.md`, `icustay_detail.md`, `rrt.md`, and `creatinine_baseline.md`; their applicable claims were checked in the supplied prober analysis. No new notes entry was added. No `unrepresentable.json` was needed.

All ViewDefinitions passed JSON validation. `uv run mimic_utils lint-sql kdigo_stages` passed cleanly. Demo execution was not run; known caveat is irrecoverable upstream DST normalization of ICU `period.start`, which can affect timing-based KDIGO branches and smoothing.
