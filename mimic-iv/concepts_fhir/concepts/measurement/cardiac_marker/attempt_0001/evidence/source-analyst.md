## Source-analyst evidence

I read `mimic-iv/concepts/measurement/cardiac_marker.sql`, the cardiac-marker DAG node, `mimic-iv/buildmimic/postgres/create.sql`, `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, and the notes-fragment README. I checked the sole `mimiciv_hosp.labevents` source, all referenced columns and datatypes, active and commented itemid literals, filters, joins, dependencies, specimen grouping, and MAX aggregations.

The source is a specimen-level numeric pivot with active itemids `51003` (troponin T), `50911` (CK-MB), and `50963` (NT-proBNP), filtered to non-null `valuenum`, grouped by `specimen_id`, and emitting `subject_id`, `hadm_id`, `charttime`, `specimen_id`, `troponin_t`, `ck_mb`, and `ntprobnp`. There are no joins or `mimiciv_derived` dependencies. The concept-level carryover was written to `mimic-iv/concepts_fhir/carryover/cardiac_marker/source-analyst.md` and recorded with the controller.

Result: source specification complete; no dataset-wide quirk was newly identified.
