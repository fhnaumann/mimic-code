# Mismatch diagnostician evidence — icustay_hourly

The full-data result is a `review`, not a mechanical mismatch. The diagnosis
read the comparison and run metadata, candidate artifacts, canonical SQL,
carryover, attempt evidence, oracle-manifest entry, `LOOP_CONTRACT.md`,
`MIMIC_NOTES.md`, and the upstream chartevents ETL SQL. The inherited divergent
dependency list is `['icustay_times']`.

Root cause is wholly inherited upstream MIMIC-on-FHIR transformation loss, not
a target SQL bug. `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts
source `charttime` through `TIMESTAMPTZ`, and line 67 writes the normalized
value to `Observation.effectiveDateTime`. Canonical `icustay_times` computes
MIN/MAX before that transformation, so MIN/MAX over the served values need not
equal the transformed canonical endpoints. A full-oracle replay found 696
selected HR rows moved across 643 stays and exactly eight dependency endpoint
changes: seven minima and one maximum.

Propagating those eight changed endpoints through the target's correct hourly
expansion reproduced every target divergence: 7 `only_oracle`, 1
`only_candidate`, and 60 `differing_conflict` rows, all conflicts on `hr`, with
zero residual. Six changed minima removed one terminal oracle row each. Stay
36521920 shifted its anchor and upper bound, producing one missing row and 60
shared keys whose candidate `hr` was one lower. Stay 32933486's changed maximum
added the sole candidate-only row. The candidate SQL correctly consumes
`FROM icustay_times`, implements ceiling/inclusive range/hourly expansion, and
has no join, filter, or ViewDefinition defect.

FHIR preserves only the normalized chart time; `issued` is transformed
storetime, not charttime. The original wall time is not recoverable by an
allowed query. Although ETL line 21 uses charttime in an opaque UUID, resource
identity cannot be parsed or inverted. Encounter periods cannot substitute for
heart-rate observation times. Recommended action is judge, not retry; no
carryover stage is invalidated.

Artifacts read:
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/run_meta.full.json`
- Target ViewDefinition and `concept.sql`
- `mimic-iv/concepts_fhir/carryover/icustay_hourly/`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_times.md` as an unconfirmed lead, independently verified

No new fragment entry was appended because the existing
`MIMIC_NOTES.d/icustay_hourly.md` entry already records this dataset-wide
chartevents MIN/MAX normalization claim.
