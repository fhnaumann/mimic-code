## Evidence

Concept: `enzyme`.

Reused the recorded source analysis from `mimic-iv/concepts_fhir/carryover/enzyme/source-analyst.md` after `mimic_utils carryover enzyme` marked `source-analyst` reusable. The canonical SQL reads only `mimiciv_hosp.labevents`, filters the exact eleven itemids with non-NULL positive `valuenum`, groups by `specimen_id`, and outputs the identifier/time columns plus eleven independent MAX analyte pivots. The manifest natural key is `specimen_id`.

Artifact reused: `mimic-iv/concepts_fhir/carryover/enzyme/source-analyst.md`. No new source analysis was needed.
