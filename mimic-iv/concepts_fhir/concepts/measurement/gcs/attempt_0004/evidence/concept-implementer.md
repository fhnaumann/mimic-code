# Concept implementer evidence

Concept `gcs`, attempt `0004`.

Read the reusable source analysis and FHIR probe mapping in
`mimic-iv/concepts_fhir/carryover/gcs/`, the authoritative `MIMIC_NOTES.md`,
and relevant chartevents fragments. Created the three ViewDefinitions and
`concept.sql` in this immutable attempt. The implementation preserves the
canonical eight-column `(stay_id, charttime)` output, exact chartevents coding
filters, identifier joins, UUIDv5 sentinel witness, and conditional one-hour
charttime recovery. The reopened defect was corrected with the required bare
`TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)`.

Checks: JSON syntax and oracle shape were checked; `uv run mimic_utils
lint-sql gcs` passed cleanly. No new dataset-wide note was appended.

Artifacts:
- `ViewDefinition.gcs_observation.json`
- `ViewDefinition.gcs_patient.json`
- `ViewDefinition.gcs_encounter.json`
- `concept.sql`
