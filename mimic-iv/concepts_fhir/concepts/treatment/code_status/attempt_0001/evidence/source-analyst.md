# Source analyst evidence — code_status attempt 0001

Concept: `code_status`

The canonical SQL is `mimic-iv/concepts/treatment/code_status.sql`.

The source reads `mimiciv_icu.chartevents`, `mimiciv_hosp.poe`,
`mimiciv_hosp.poe_detail`, and `mimiciv_icu.icustays`. It outputs
`subject_id`, `hadm_id`, `stay_id`, `charttime`, `fullcode`, `cmo`, `dni`, and
`dnr`. Filters are chartevents itemid `223758`, POE `order_type = 'General
Care'`, and `order_subtype = 'Code status'`; exact chart-value and
`field_value` literals, including whitespace, are preserved in
`carryover/code_status/source-analyst.md`.

The POE/detail join is INNER on `poe_id`. The ICU-stay join is LEFT on matching
`hadm_id` and inclusive `ordertime`/`intime`/`outtime` bounds. There are no
derived dependencies, aggregations, windows, grouping, ordering, or
deduplication. The oracle has no natural key and uses full-tuple multiset
comparison with 269,072 rows.

FHIR implications: chart events use the ICU chartevents coding system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and code
`223758`; POE statuses require exact free-text matching. No new dataset-wide
quirk was identified and no `MIMIC_NOTES.d/code_status.md` append was needed.

Files read: `AGENTS.md`, the DAG, `MIMIC_NOTES.md`, relevant
`MIMIC_NOTES.d` fragments, source DDL, generated DuckDB SQL, oracle manifest,
loop contract, and the current attempt directory.

Artifacts produced:
- `mimic-iv/concepts_fhir/carryover/code_status/source-analyst.md`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/evidence/source-analyst.md`
