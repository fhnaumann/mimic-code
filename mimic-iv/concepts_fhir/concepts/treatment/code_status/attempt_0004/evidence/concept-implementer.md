Evidence block — `code_status`, attempt 0004

Read `AGENTS.md`, the canonical `mimic-iv/concepts/treatment/code_status.sql`,
the reusable `carryover/code_status/source-analyst.md` and
`carryover/code_status/fhir-prober.md`, the complete `MIMIC_NOTES.md`,
`MIMIC_NOTES.d/README.md`, all existing `MIMIC_NOTES.d/*.md` fragments, the
manifest entry, the canonical ViewDefinition example, the loop contract, and
the prior code-status attempts and reopen evidence. The attempt directory was
empty before authoring; no existing artifact was replaced.

The implementation has four ViewDefinitions: chart `Observation`, `Patient`,
ICU `Encounter`, and hospital `Encounter`. It filters the chart stream inside
the coding `forEach` by the exact chartevents system and code `223758`, joins
only on opaque FHIR reference/resource keys, recovers MIMIC identifiers from
`identifier.value`, preserves the two effective-time variants, and derives all
four status flags from `value.ofType(string)`. The SQL emits the representable
chartevents branch with `UNION ALL`-compatible multiplicity and explicit casts
for all eight manifest columns. It deliberately does not map the absent
General Care/Code status POE branch to `MedicationRequest`; that missing branch
changes row inclusion and is essential representation loss for the equivalence
judge, not an automatically accepted partial-table claim.

The manifest columns and order were checked as
`subject_id INTEGER`, `hadm_id INTEGER`, `stay_id INTEGER`, `charttime
TIMESTAMP`, and four `INTEGER` status flags. JSON parsing passed for all four
ViewDefinitions. `uv run mimic_utils lint-sql code_status` passed cleanly.
No `unrepresentable.json` was produced because no individual oracle output
column is absent from the represented chart Observation branch; the essential
POE row-inclusion loss is documented here rather than falsely declaring an
ordinary output column NULL. No new dataset-wide quirk was established, so
`MIMIC_NOTES.d/code_status.md` was not appended.

Artifacts produced:

- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0004/ViewDefinition.cs_chart.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0004/ViewDefinition.cs_patient.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0004/ViewDefinition.cs_icu.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0004/ViewDefinition.cs_hosp.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0004/concept.sql`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0004/evidence/concept-implementer.md`
