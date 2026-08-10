Concept: coagulation

Read the canonical SQL `mimic-iv/concepts/measurement/coagulation.sql`, the loop contract, AGENTS.md, the DAG, MIMIC_NOTES.md, and relevant notes fragments. The source is a dependency-free pivot over `mimiciv_hosp.labevents`, retaining exact itemids 51196, 51214, 51297, 51237, 51274, and 51275 with `valuenum IS NOT NULL`, grouped by `specimen_id`. It emits subject_id, hadm_id, charttime, specimen_id, and six nullable DOUBLE analyte columns. Metadata uses independent MAX aggregates; there are no joins, windows, time bounds, or derived dependencies. The natural key is `specimen_id`, with 1,543,003 oracle rows.

Reusable carryover was written and recorded at `mimic-iv/concepts_fhir/carryover/coagulation/source-analyst.md`; `uv run mimic_utils carryover-record coagulation --stage source-analyst` succeeded. No attempt implementation artifacts were created and no new dataset-wide quirk was found.
