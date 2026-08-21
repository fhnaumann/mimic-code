# Source-analyst evidence — `urine_output_rate`

The source analyst read `mimic-iv/concepts/measurement/urine_output_rate.sql`,
the DAG metadata, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, and the relevant
provisional fragments (`urine_output.md`, `first_day_urine_output.md`, and
`weight_durations.md`).

The canonical query has direct ICU `icustays` and `chartevents` inputs and
consumes the completed `urine_output` and `weight_durations` dependencies. It
filters chartevents to item `220045` within strict one-month-expanded ICU
bounds, computes successive urine measurement intervals with `LAG`, performs
inclusive 23-hour self-join aggregation for 6/12/24-hour windows, and applies a
strict-start/inclusive-end positive-weight interval join. The intended grain
and comparison key are `(stay_id, charttime)`; the manifest has 13 output
columns plus required opaque `icu_encounter_key` and `patient_key` columns.

The reusable analysis was written to
`mimic-iv/concepts_fhir/carryover/urine_output_rate/source-analyst.md` and
recorded with `carryover-record`. Timing normalization and inherited
dependency interval effects can affect inclusion, keys, windows, and rates;
dependencies must remain unqualified `urine_output` and `weight_durations`
views rather than being rederived.
