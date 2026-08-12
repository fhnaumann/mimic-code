# Source-analyst evidence

The source analyst read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the
existing `MIMIC_NOTES.d` fragments, the DAG, the canonical
`mimic-iv/concepts/medication/epinephrine.sql`, the MIMIC-IV DDL/constraints,
and the oracle manifest. The SQL source SHA256 matched the DAG. It is a
single projection from `mimiciv_icu.inputevents`, filtered only by the literal
`itemid = 221289`, with no joins, dependencies, aggregation, deduplication, or
unit/range filtering. The six outputs are `stay_id`, `linkorderid`,
`rate AS vaso_rate`, `amount AS vaso_amount`, `starttime`, and `endtime`.
The manifest reports 24,470 full rows and comparison key
`(linkorderid, starttime)`.

The reusable source analysis was written and recorded at
`mimic-iv/concepts_fhir/carryover/epinephrine/source-analyst.md`. No
dataset-wide quirk was reported and no attempt artifact was edited by the
agent.
