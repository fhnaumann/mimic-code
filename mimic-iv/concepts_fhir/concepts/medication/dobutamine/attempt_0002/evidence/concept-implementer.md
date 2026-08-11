# Concept implementer evidence

Concept: `dobutamine`  
Attempt: `0002`

Read the reusable source analysis and FHIR probe at
`mimic-iv/concepts_fhir/carryover/dobutamine/`, along with
`mimic-iv/concepts_fhir/MIMIC_NOTES.md` and relevant medication fragments.

Created the Spark-compatible ViewDefinitions and derived SQL. The port filters
the ICU medication coding system plus exact code `221653`, joins the ICU
Encounter identifier for `stay_id`, projects both `effective[x]` variants,
casts quantities to `FLOAT`, parses datetimes with `TIMESTAMP_NTZ`, and emits
the six manifest columns in order. `linkorderid` is a typed NULL and is
documented in `unrepresentable.json` because the FHIR ETL does not represent
it.

Artifacts:
- `ViewDefinition.medication_administration.json`
- `ViewDefinition.encounter_icu.json`
- `concept.sql`
- `unrepresentable.json`

No existing attempt artifact was edited or replaced; no dataset-wide notes
finding was added.
