# Source-analyst evidence

The source analyst read the canonical milrinone SQL, DAG metadata, source DDL and constraints, oracle manifest, LOOP_CONTRACT.md, AGENTS.md, MIMIC_NOTES.md, and relevant MIMIC_NOTES.d fragments. The concept is a dependency-free level-0 extraction from `mimiciv_icu.inputevents`, filtered exactly by `itemid = 221986`, with direct outputs `stay_id`, `linkorderid`, `rate AS vaso_rate`, `amount AS vaso_amount`, `starttime`, and `endtime`. It has no joins, aggregation, windows, or temporal filters. The full oracle has 9,573 rows and comparator key `(stay_id, starttime)`.

The reusable analysis was written to `mimic-iv/concepts_fhir/carryover/milrinone/source-analyst.md` and recorded in the carryover ledger. The likely FHIR stream is ICU `MedicationAdministration`; `linkorderid` may be absent and must not be recovered from opaque resource ids. Artifact produced: `mimic-iv/concepts_fhir/carryover/milrinone/source-analyst.md`.
