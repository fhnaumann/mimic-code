# Source analyst evidence

The source analyst read the DAG-resolved canonical SQL, `vasoactive_agent.sql`,
`MIMIC_NOTES.md`, and the relevant provisional medication fragments. The
canonical input is `mimiciv_derived.vasoactive_agent`; it has no raw-table joins
or other derived dependencies. It selects `stay_id`, `starttime`, `endtime`,
and five vasoactive rate columns (`norepinephrine`, `epinephrine`,
`phenylephrine`, `dopamine`, `vasopressin`), keeps rows where at least one of
the five rates is non-NULL, and computes interval-grain equivalent dose with
the source formula and four-place rounding. No coded literals, grouping,
windows, or aggregations are used.

Reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/norepinephrine_equivalent_dose/source-analyst.md`
and recorded in its carryover ledger. No new dataset-wide quirk was
established at this stage; patientweight loss, conditional effective times,
and decimal precision remain probing leads.

Artifacts: this evidence file and the reusable carryover analysis above.
