## Source analyst evidence

Concept `sofa`; SQL read: `mimic-iv/concepts/score/sofa.sql`. Checked the DAG
node, SHA256, all 13 dependencies, raw table `mimiciv_icu.icustays`, and
derived tables `icustay_hourly`, `bg`, `ventilation`, `vitalsign`, `gcs`,
`enzyme`, `chemistry`, `complete_blood_count`, `urine_output_rate`,
`epinephrine`, `norepinephrine`, `dopamine`, and `dobutamine`. Traced all
columns, joins, filters, literals, score boundaries, aggregates, 24-row
window, 29-column output shape, types, and `(stay_id, starttime)` natural key.
Direct coding literals are `specimen = 'ART.'` and
`ventilation_status = 'InvasiveVent'`; no direct itemid or ICD filters occur in
`sofa.sql`. Relevant notes and dependency SQLs were checked.

Result: SOFA is an hourly ICU-spine derivation using completed dependency temp
views, six hourly component scores, and rolling 24-hour maxima. Reusable
analysis was also written and recorded at
`mimic-iv/concepts_fhir/carryover/sofa/source-analyst.md`.

Artifacts: `mimic-iv/concepts_fhir/carryover/sofa/source-analyst.md` and this
evidence file. No ViewDefinition or `concept.sql` was authored and canonical
SQL was not modified.
