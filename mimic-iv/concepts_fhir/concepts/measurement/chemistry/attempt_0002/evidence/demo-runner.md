Evidence block

Concept: `chemistry`; attempt: `attempt_0002`; recorded verdict: `shape_ok`.

`uv run mimic_utils run-demo chemistry` refused to re-execute because the write-once artifact `candidate.demo.parquet` already exists. This is an artifact guard, not an execution failure. The existing `shape.demo.json` records `executed: true` and the demo run had already completed.

Column-name comparison matched the manifest exactly: `subject_id, hadm_id, charttime, specimen_id, albumin, globulin, total_protein, aniongap, bicarbonate, bun, calcium, chloride, creatinine, glucose, sodium, potassium`; no missing or extra columns. Existing Parquet inspection confirmed compatible types: integer identifiers, timestamp `charttime`, and double analyte columns. Existing candidate demo row count is 3,289 versus full oracle 3,811,523; row count is explicitly non-gating.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002/candidate.demo.parquet/`
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002/shape.demo.json` (`verdict: shape_ok`)

No implementation artifacts, state transitions, or notes were modified by the runner.
