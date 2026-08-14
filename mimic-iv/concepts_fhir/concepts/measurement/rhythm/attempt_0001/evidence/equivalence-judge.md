# Equivalence-judge evidence — rhythm

The independent judge assessed attempt_0001's full-data `review`, tier
`attributed`. It returned **bug**, not because the port mapping was defective,
but because the comparator's attribution citation list omitted the ETL writer
for this concept's source element. The candidate reads
`Observation.effectiveDateTime`; the relevant upstream statement is
`/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`,
which casts `ce.charttime` to `TIMESTAMPTZ` and writes `effectiveDateTime`.

The judge confirmed the machine proof and rarity: 95 conflicts, 645
oracle-only rows, and 42 candidate-only rows were fully attributed, with
603 key collisions and 42 repaired pairs, zero residuals, and 99.9874%
identical rows. It confirmed that the candidate's aggregation is equivalent
to `rhythm.sql` over the transformed FHIR data and that resource IDs were used
only for equality joins, never inverted. There are no divergent dependencies.

The comparator citation registry was corrected to include
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`; this is a comparator
correctness fix requiring a new immutable attempt and full run. The judge read
`LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, the canonical SQL, the attempt
artifacts, comparison/run metadata, and the upstream ETL file. No files were
modified by the judge.
