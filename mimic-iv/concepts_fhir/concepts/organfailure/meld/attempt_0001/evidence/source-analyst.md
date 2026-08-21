# Source-analyst evidence — meld

The source analyst read `mimic-iv/concepts/organfailure/meld.sql`, DAG metadata,
dependency SQL/context, MIMIC DDL, dependency carryover analyses, and the MELD
oracle manifest entry. The concept is DAG level 2 with exact dependencies
`first_day_lab` and `first_day_rrt`; candidate SQL must consume the completed
dependency temp views by those unqualified stems.

The canonical query drives from `mimiciv_icu.icustays` and left joins both
dependencies on `stay_id`. It has no direct coded filters, WHERE clause,
aggregation, or window. It emits one row per ICU `stay_id`, with
`subject_id`, `hadm_id`, `stay_id`, MELD score columns, RRT, and the four
dependency lab inputs. The executable CASE logic applies the documented sodium,
creatinine/RRT, bilirubin, INR, initial-MELD cap/rounding, and sodium correction
rules. `intime` and `outtime` are selected but unused. No new dataset-wide quirk
was reported for promotion to `MIMIC_NOTES.d/meld.md`.

Carryover produced: `mimic-iv/concepts_fhir/carryover/meld/source-analyst.md`.
No attempt artifact was created by this stage.
