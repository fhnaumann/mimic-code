Concept `sepsis3`; source-analysis stage.

Read the canonical SQL at `mimic-iv/concepts/sepsis/sepsis3.sql`, the DAG files,
`MIMIC_NOTES.md`, relevant provisional fragments for `sofa` and
`suspicion_of_infection`, the dependency SQL, and the oracle manifest.

The concept reads only `mimiciv_derived.sofa` and
`mimiciv_derived.suspicion_of_infection`; it has no direct hospital/ICU tables,
itemid filters, ICD filters, or other code systems. The analysis documented all
dependency columns, output columns/types, source key `stay_id`, the
`sofa_24hours >= 2` and `soi.stay_id IS NOT NULL` predicates, the inclusive
`-48/+24` hour inner join, `rn_sus = 1`, and the `ROW_NUMBER()` window. There are
no aggregations. The result selects the earliest qualifying SOFA/suspicion row
per ICU stay.

Reusable artifacts produced by the stage:
- `mimic-iv/concepts_fhir/carryover/sepsis3/source-analyst.md`
- `mimic-iv/concepts_fhir/carryover/sepsis3/carryover.json`

No new dataset-wide quirk was reported; no `MIMIC_NOTES.d/sepsis3.md` entry was
added at this stage.
