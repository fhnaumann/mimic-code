# Concept-implementer evidence — lods attempt_0001

The implementer produced five write-once artifacts in the attempt directory:

- `ViewDefinition.patient.json`
- `ViewDefinition.hospital_encounter.json`
- `ViewDefinition.icu_encounter.json`
- `ViewDefinition.cpap_observation.json`
- `concept.sql`

The implementation uses exact system-plus-code filtering for chartevents item
`226732`, the ICU/hospital/patient identifier and reference-key spine, the six
completed dependency views by unqualified stem, `TIMESTAMP_NTZ` datetime casts,
source interval boundaries, ordered score CASE branches, and nullable component
scores with a zero-filled total. Required opaque companion keys are retained;
resource IDs are not parsed or regenerated. No `unrepresentable.json` was
needed.

`uv run mimic_utils lint-sql lods` completed cleanly, and `git diff --check`
was clean. The stale `first_day_gcs` dependency attempt was consumed unchanged;
its inherited divergence remains for the full comparison and judge.
