# Evidence — source-analyst (reused carryover)

Read the immutable `carryover/height/source-analyst.md`, canonical
`mimic-iv/concepts/measurement/height.sql`, and the full-oracle manifest.
`height` is a level-0 concept with no dependencies. The source reads ICU
`chartevents` itemids 226707 (inches) and 226730 (centimetres), full-outer
joins on `subject_id + charttime`, prefers the centimetre stream, converts
inches by 2.54, rounds to two decimals, and filters strict bounds 120 < height
< 230. Target shape is `(subject_id INTEGER, stay_id INTEGER, charttime
TIMESTAMP, height DECIMAL(38,2))`; full natural key is `stay_id`.

Artifact reused: `mimic-iv/concepts_fhir/carryover/height/source-analyst.md`.
