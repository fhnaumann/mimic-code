Evidence block — Concept: dopamine.

The source analyst read `mimic-iv/concepts/medication/dopamine.sql`, the DAG, loop contract, curated MIMIC notes, relevant fragments, and source DDL. The source is a dependency-free extraction from `mimiciv_icu.inputevents`, filtered exactly to `itemid = 221662`, with columns `stay_id`, `linkorderid`, `rate` as `vaso_rate`, `amount` as `vaso_amount`, `starttime`, and `endtime`. There are no joins, aggregations, windows, or derived dependencies. The manifest natural key is `stay_id, starttime`.

Reusable artifact produced: `mimic-iv/concepts_fhir/carryover/dopamine/source-analyst.md`, recorded with the carryover ledger. No attempt artifact was modified by the analyst.
