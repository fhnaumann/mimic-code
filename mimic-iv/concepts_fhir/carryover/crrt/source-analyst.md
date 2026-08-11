## CRRT source analysis

- Canonical SQL: `mimic-iv/concepts/treatment/crrt.sql`.
- Source: `mimiciv_icu.chartevents`, filtered to the 19 CRRT itemids named in
  the SQL and `value IS NOT NULL`.
- Grain: `(stay_id, charttime)`, pivoted with `MAX`.
- Output: `stay_id`, `charttime`, 14 numeric FLOAT measures, 3 VARCHAR
  measures, and integer flags `system_active`, `clots`, `clots_increasing`,
  `clotted`.
- Item 224146 supplies the four categorical flags; item 227290 supplies
  `crrt_mode`; the remaining item mappings are recorded in the source SQL.
- Full oracle key: `(stay_id, charttime)`; full oracle rows: 287,152.
