Evidence block — Concept `height`.

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, `MIMIC_NOTES.d/README.md`, every existing `MIMIC_NOTES.d` fragment, the height DAG node, canonical SQL, `chartevents` DDL, and the oracle manifest. The source SQL reads `mimiciv_icu.chartevents` twice, outputs `subject_id`, `stay_id`, `charttime`, and rounded centimetre `height`, filters itemids `226707` and `226730`, requires `valuenum IS NOT NULL` and strict `120 < height < 230`, and uses a `FULL OUTER JOIN` on `subject_id` and `charttime` only. It has no derived dependencies or aggregations and uses proprietary ICU itemid coding.

Produced/reused analysis: `mimic-iv/concepts_fhir/carryover/height/source-analyst.md`, recorded in `mimic-iv/concepts_fhir/carryover/height/carryover.json`. No attempt artifacts were modified by the analyst and no dataset-wide quirk was reported for this evidence.
