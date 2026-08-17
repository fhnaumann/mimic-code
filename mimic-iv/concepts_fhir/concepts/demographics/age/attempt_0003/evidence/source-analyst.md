# Evidence: source-analyst (reused)

The source-analysis stage was reused from the current concept carryover at
`mimic-iv/concepts_fhir/carryover/age/source-analyst.md`. It identifies
`mimiciv_hosp.admissions` joined to `mimiciv_hosp.patients` on `subject_id`,
with no filters or derived dependencies, and the outputs `subject_id`,
`hadm_id`, `admittime`, `anchor_age`, `anchor_year`, and the canonical age
formula. The manifest natural key is `hadm_id`.

The carryover was read and passed to the re-run fhir-prober. No new
source-analyst subagent was required by the resume plan.

Artifact consulted: `mimic-iv/concepts_fhir/carryover/age/source-analyst.md`.
