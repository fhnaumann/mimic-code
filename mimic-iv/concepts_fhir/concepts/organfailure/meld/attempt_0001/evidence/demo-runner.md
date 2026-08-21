# Demo-runner evidence — meld

`uv run mimic_utils run-demo meld` executed successfully using embedded
Pathling on Spark over the local demo Delta warehouse. The shape verdict was
`shape_ok`/pass, so the attempt may proceed to full data; this is not a
correctness result.

The candidate produced 140 demo rows. All ten oracle columns were present with
compatible types: the three identifiers were integer-compatible, `meld_initial`
was `DECIMAL(38,1)`, `meld` was `DOUBLE`, `rrt` was integer-compatible, and all
four dependency outputs were `DOUBLE`. The required informational key columns
`encounter_key`, `icu_encounter_key`, and `patient_key` were present. There were
no missing or incompatible columns.

Artifacts produced:

- `mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0001/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/organfailure/meld/attempt_0001/shape.demo.json`

Row count was reported only and was not used as a gate.
