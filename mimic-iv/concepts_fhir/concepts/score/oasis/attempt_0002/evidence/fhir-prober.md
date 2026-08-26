# FHIR-prober evidence

Concept: `oasis`; attempt: `0002`.

This stage reused the valid source analysis and re-probed the invalidated FHIR
mapping over the authoritative local Delta with embedded Pathling 9.6.0 /
Spark 4.0.2. It verified that hospital `Encounter.priority.coding` uses
`http://terminology.hl7.org/CodeSystem/v3-ActPriority` and exact code `EL`;
the 13 EL rows matched source `admission_type='ELECTIVE'` exactly. This
supersedes the attempt-0001 class `AMB` proxy. Identifier, period, subject,
partOf, opaque-key, Observation code/effective/value, and dependency-boundary
mappings were also rechecked.

The probe confirmed that FHIR retains one earliest service coding per hospital
Encounter while source `services` has 319 rows over 275 admissions and
`transfertime`/later service history is absent. The previously diagnosed 54
later-service elective false negatives therefore remain an intrinsic,
essential loss to be presented to the judge after correcting the priority
mapping. No resource id was parsed or used as a semantic side channel.

The rebuilt numeric chartevent component probe also found component text/code/
system for all OASIS GCS item resources (`220739`, `223900`, `223901`) and the
expected partial ventilator label coverage. This new dataset-wide finding was
appended to the owned fragment:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/oasis.md`.

Reusable mapping was overwritten and recorded at
`mimic-iv/concepts_fhir/carryover/oasis/fhir-prober.md` and
`mimic-iv/concepts_fhir/carryover/oasis/carryover.json`. No implementation
artifact, execution, state transition, or commit was performed by this stage.
