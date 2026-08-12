# Source analyst evidence

Concept `inflammation`, attempt `0001`.

The canonical source is `mimic-iv/concepts/measurement/inflammation.sql`.
It reads `mimiciv_hosp.labevents` columns `subject_id`, `hadm_id`, `charttime`,
`specimen_id`, `itemid`, and `valuenum`; filters executable itemid `50889`,
non-null `valuenum`, and `valuenum > 0`; and groups by `specimen_id`. The
outputs are `MAX(subject_id)`, `MAX(hadm_id)`, `MAX(charttime)`,
`specimen_id`, and positive CRP `MAX(CASE WHEN itemid = 50889 THEN valuenum
END)`. The natural key is `specimen_id`; there are no joins or derived
dependencies. Commented itemid `51652` is not part of the source semantics.

Relevant dataset notes were checked, including lab item coding, comparator
text handling, specimen identifiers, encounter coverage, and datetime casts.
No new dataset-wide quirk was identified at this stage.

Reusable analysis was written to and recorded from:
`mimic-iv/concepts_fhir/carryover/inflammation/source-analyst.md`.
