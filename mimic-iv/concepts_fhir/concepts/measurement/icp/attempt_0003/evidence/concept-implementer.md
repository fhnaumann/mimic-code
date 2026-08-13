Evidence block

Concept: `icp`; attempt: `0003`.

The implementer read `AGENTS.md`, the reusable source and FHIR analyses in
`mimic-iv/concepts_fhir/carryover/icp/`, `MIMIC_NOTES.md`, and relevant owned
and sibling fragments. It produced three ViewDefinitions and `concept.sql`.
The output uses the exact chartevents coding system and item codes `220765` and
`227989`, equality joins on opaque resource/reference keys only, identifier
values for `subject_id`/`stay_id`, `TIMESTAMP_NTZ` for `charttime`, Quantity
casting, and grouped strict-range `MAX` semantics. It does not reconstruct or
parse Observation ids and does not apply the superseded UUID-based DST repair.

`uv run mimic_utils lint-sql icp` passed cleanly. No new dataset-wide quirk was
discovered or appended to `MIMIC_NOTES.d/icp.md`.

Artifacts:
- `ViewDefinition.icp_observation.json`
- `ViewDefinition.icp_patient.json`
- `ViewDefinition.icp_icu_encounter.json`
- `concept.sql`
