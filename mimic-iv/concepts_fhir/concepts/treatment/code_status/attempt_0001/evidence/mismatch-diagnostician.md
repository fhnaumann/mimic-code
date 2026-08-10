# Mismatch diagnostician evidence — code_status attempt 0001

The full result is `review`, tier `contested`, classification
`unavailable_no_key`, not a machine-provable mismatch. Schema matched exactly.

The 9 `only_candidate` rows are one-for-one timestamp substitutions: each has
identical subject, admission, ICU stay, and status flags to an oracle tuple,
but the FHIR timestamp is exactly one hour later (source 02:xx versus FHIR
03:xx). The source chart rows and candidate rows both number 71,141; 71,132
chart tuples are exact and 9 are transformed. The separate 197,931-row deficit
is the absent POE code-status branch, yielding 197,940 `only_oracle` rows.

Root cause: upstream ETL transformation loss in
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, which casts naive
`chartevents.charttime` through `TIMESTAMPTZ` and writes only the normalized
value to `Observation.effectiveDateTime`. The normalized timestamp is not
invertible from FHIR; conditionally subtracting an hour would manufacture
errors on genuine 03:xx values. Attempt `ViewDefinition.cs_chart.json:13-19`
and `concept.sql:9-30,47-65` preserve the served value correctly. No filter,
join, status mapping, NULL handling, hard-coded duplicate, or carryover stage
is at fault. Recommended route: convene the equivalence judge; do not retry.

The dataset-wide finding was appended to the owned fragment:
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/code_status.md`, section
“Chartevents effectiveDateTime irreversibly normalizes DST-gap charttime”.
`MIMIC_NOTES.md` and immutable attempt artifacts were not edited.

Files examined included `comparison.full.json`, `run_meta.full.json`,
`shape.demo.json`, all four ViewDefinitions, `concept.sql`, source SQL,
carryovers, the oracle manifest, `LOOP_CONTRACT.md`, all notes/fragments, and
`/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql`.
