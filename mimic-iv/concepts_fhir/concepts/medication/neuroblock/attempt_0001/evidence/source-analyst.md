# Source-analyst evidence — neuroblock

Read the canonical SQL `mimic-iv/concepts/medication/neuroblock.sql`, DAG,
oracle manifest, source DDL/constraints, LOOP_CONTRACT.md, MIMIC_NOTES.md, and
relevant medication/ICU note fragments. Confirmed a dependency-free level-0
query over `mimiciv_icu.inputevents`, selecting `stay_id`, `orderid`, `rate AS
drug_rate`, `amount AS drug_amount`, `starttime`, and `endtime`, filtered to
itemids 222062 and 221555 with `rate IS NOT NULL`. There are no joins,
aggregations, windows, or transformations; the full oracle has 14,174 rows and
uses `orderid` as its empirical comparison key.

The reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/neuroblock/source-analyst.md` and recorded in
the carryover ledger. No implementation artifact or commit was produced by
this stage.
