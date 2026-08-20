# Evidence: source-analyst (reused)

`source-analyst` was reused from the recorded carryover because the canonical source and DAG analysis are unchanged. Read:
- `mimic-iv/concepts_fhir/carryover/urine_output/source-analyst.md`
- `mimic-iv/concepts/measurement/urine_output.sql`
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`

Result: the source filters twelve exact outputevents itemids, negates positive item `227488`, and sums at `(stay_id, charttime)`; target shape is `stay_id INTEGER`, `charttime TIMESTAMP`, `urineoutput DOUBLE`, with no derived dependency. The carryover remains valid for attempt 0003.

Artifact reused: `mimic-iv/concepts_fhir/carryover/urine_output/source-analyst.md`.
