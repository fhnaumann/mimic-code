# Source analyst evidence

Reused carryover analysis for `crrt` (attempt 1). The canonical source is `mimic-iv/concepts/treatment/crrt.sql`, filtered to the named CRRT itemids and non-null values, pivoted at `(stay_id, charttime)` with `MAX`, with 24 output columns and full-data key `(stay_id, charttime)`.

Carryover artifact: `mimic-iv/concepts_fhir/carryover/crrt/source-analyst.md`.
