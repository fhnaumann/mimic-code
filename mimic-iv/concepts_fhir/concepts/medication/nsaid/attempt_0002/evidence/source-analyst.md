# Evidence — source-analyst

Concept `nsaid`, attempt `0002` (reused carryover from attempt `0001`).

Read the canonical SQL, DAG metadata, prescription schema/constraints, curated
MIMIC notes, and relevant fragments. Confirmed one `mimiciv_hosp.prescriptions`
source scanned through a distinct drug classifier and exact join, with 20
verbatim case-insensitive substring predicates. The output is one qualifying
prescription row with `subject_id`, `hadm_id`, original `drug` as `nsaid`, and
nullable `starttime`/`stoptime`; there are no dependencies.

Reusable analysis: `mimic-iv/concepts_fhir/carryover/nsaid/source-analyst.md`.
