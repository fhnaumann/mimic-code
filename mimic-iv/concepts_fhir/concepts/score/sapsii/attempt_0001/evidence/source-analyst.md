# Source-analyst evidence — sapsii attempt_0001

The source analyst read `mimic-iv/concepts/score/sapsii.sql`, the DAG, the loop
contract, `MIMIC_NOTES.md`, the relevant notes fragments, the oracle manifest,
and the MIMIC-IV schema. The canonical SQL is 549 lines, has DAG dependencies
`age`, `bg`, `chemistry`, `complete_blood_count`, `enzyme`, `gcs`,
`urine_output`, `ventilation`, and `vitalsign`, and produces one row per ICU
stay keyed by `stay_id` (73,181 oracle rows).

It identified the ICU/hospital source tables, exact item/value and ICD-9/ICD-10
predicates, first-24-hour temporal windows, CPAP interval expansion, invasive
ventilation overlap, all dependency joins, aggregations/windows, scoring
branches, logistic probability formula, final columns/types, required FHIR
resource-key columns, and semantically essential identity/time/value inputs.
The dependency boundary must be preserved with unqualified candidate views
named by the nine dependency stems. No attempt artifacts were authored by the
analyst. The concept-level reusable analysis is at
`mimic-iv/concepts_fhir/carryover/sapsii/source-analyst.md`; it was recorded in
`carryover.json`.
