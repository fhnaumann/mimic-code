## Evidence

The source analysis read `mimic-iv/concepts/treatment/crrt.sql`,
`mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`,
`mimic-iv/concept_dag/concept_dag.json`, `MIMIC_NOTES.md`,
`MIMIC_NOTES.d/README.md`, and the relevant `MIMIC_NOTES.d/code_status.md`
fragment. CRRT is a level-0 concept with no dependencies and source table
`mimiciv_icu.chartevents`.

The source filters `value IS NOT NULL` and itemids
`227290, 224146, 224149, 224144, 228004, 225183, 225977, 224154, 224151,
224150, 225958, 224145, 224191, 228005, 228006, 225976, 224153, 224152,
226457`. It pivots by `(stay_id, charttime)` using `MAX`, with categorical
value mappings for item 224146. The target has 24 columns: `stay_id` INTEGER,
`charttime` TIMESTAMP, 14 numeric FLOAT columns, 3 VARCHAR columns, and four
INTEGER flags (`system_active`, `clots`, `clots_increasing`, `clotted`).
The immutable full oracle has 287,152 rows keyed by `(stay_id, charttime)`.

Item-derived Observation codes preserve source itemids; chartevent categorical
values are strings. The chartevent ETL can omit NULL-valued rows and one known
duplicate, and can normalize DST-gap timestamps; applicability to CRRT remains
to be checked by the FHIR probe.

No dataset-wide quirk was newly established by this source-only stage, and no
FHIR probing or implementation was performed.
