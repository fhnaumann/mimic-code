# Source-analyst evidence

Read the canonical `medication/dobutamine.sql`, DAG metadata, AGENTS.md, LOOP_CONTRACT.md, MIMIC_NOTES.md, and relevant MIMIC_NOTES.d fragments. Verified the DAG hash and dependency status. The source is a dependency-free extraction from `mimiciv_icu.inputevents`, filtered exactly by `itemid = 221653`, with no joins, aggregation, windowing, unit conversion, or extra predicates. It emits `stay_id`, `linkorderid`, `rate AS vaso_rate`, `amount AS vaso_amount`, `starttime`, and `endtime`; the full manifest key is `(stay_id, starttime)`.

Artifact produced: `mimic-iv/concepts_fhir/carryover/dobutamine/source-analyst.md`; carryover ledger recorded the stage in `mimic-iv/concepts_fhir/carryover/dobutamine/carryover.json`. No dataset-wide quirk was found to append.
