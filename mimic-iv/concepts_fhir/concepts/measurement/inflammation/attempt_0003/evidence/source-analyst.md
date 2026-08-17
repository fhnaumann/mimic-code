# Evidence: source-analyst (reused carryover)

The source analysis was reused from `mimic-iv/concepts_fhir/carryover/inflammation/source-analyst.md` under the controller's carryover ledger. It identifies `mimic-iv/concepts/measurement/inflammation.sql` as a level-0, dependency-free aggregate: positive, non-null labevents `itemid=50889`, grouped by `specimen_id`, with independent `MAX` values for `subject_id`, `hadm_id`, `charttime`, and CRP `valuenum`. The expected output is 117,898 rows with columns `subject_id`, `hadm_id`, `charttime`, `specimen_id`, and `crp`; `specimen_id` is the natural key.

Artifact reused: `mimic-iv/concepts_fhir/carryover/inflammation/source-analyst.md`.
