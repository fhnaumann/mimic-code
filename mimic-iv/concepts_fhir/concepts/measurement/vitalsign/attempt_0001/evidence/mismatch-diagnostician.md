## Evidence

The diagnostician read the full comparison, run metadata, attempt SQL/ViewDefinitions, canonical `vitalsign.sql`, curated `MIMIC_NOTES.md`, and relevant sibling fragments as provisional leads. It confirmed the candidate's joins, code filters, one-resource-per-coded-Observation mapping, and `(subject_id, stay_id, charttime)` grouping are correct; no carryover stage is invalidated and no new attempt is needed.

The 343 candidate-only rows, 1,105 of the 1,106 oracle-only rows, and all 758 conflicts are one upstream DST transformation propagated through grouping: `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` normalizes charttime before writing `Observation.effectiveDateTime`, while the canonical and candidate SQL group at the same grain. The comparator's full replay accounts for these rows; resource IDs were not used.

The single residual oracle-only group is the exact hard-coded ETL omission `(stay_id=34934165, charttime='2151-10-03 05:14:00')` at `mimic-fhir/sql/fhir_observation_chartevents.sql:34-37`. A full-oracle probe found two identical selected `itemid=220621` rows (`subject_id=13793458`, `value='96'`, `valuenum=96`), which canonical grouping emits as one `glucose=96` row. The ETL removes the whole group before FHIR creation, so no FHIR query can recover it. Because it changes row inclusion and the concept's grouping grain, the residual is essential loss for judge assessment.

The diagnostician appended the dataset-wide finding to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/vitalsign.md`. No SQL/ViewDefinition fix is recommended.
