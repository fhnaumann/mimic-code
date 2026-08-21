# FHIR prober evidence — icustay_hourly

The authoritative Delta probe used embedded Pathling 9.6.0/Spark 4.0.2 with
UTC session timezone and the demo DuckDB oracle. It read the source analysis,
canonical and dependency SQL, `MIMIC_NOTES.md`, relevant provisional
fragments, the completed `icustay_times` attempt, and local ICU
Observation/Encounter ETL SQL.

The target must consume the completed `icustay_times` derived view and must not
rederive it. The published dependency has `intime_hr`, `outtime_hr`,
`patient_key`, `encounter_key`, and `icu_encounter_key`; identifier columns
including `stay_id` are stripped when paired resource keys exist. The target
joins `icu_encounter_key` to an ICU Encounter view, obtains numeric `stay_id`
from the exact ICU Encounter identifier system/value, and emits
`icu_encounter_key` and `patient_key` verbatim as opaque required keys.

The dependency's transitive heart-rate mapping is ICU chartevents Observation
code system plus exact code `220045`; 13,913/13,913 codings mapped one-to-one
to resources. Effective dateTime was populated for 13,913/13,913 target rows,
while Period and instant variants were empty. Direct `TIMESTAMP_NTZ` parsing
is required before aggregation. Selected ICU Encounters and their keys,
references, and periods were populated 140/140. The FHIR-to-oracle dependency
aggregate and the generated target grid both matched the demo oracle exactly:
140/140 endpoint rows and 15,615/15,615 `(stay_id, hr, endtime)` tuples. The
source `DATETIME_DIFF(..., HOUR)` boundary semantics must be preserved rather
than using fractional elapsed-duration ceiling.

The probe also confirmed the dataset-wide provisional finding recorded in
`MIMIC_NOTES.d/icustay_hourly.md`: chartevents ETL TIMESTAMPTZ normalization
can collapse source spring-forward-gap times before per-stay MIN/MAX. Two HR
source 02:00 groups became FHIR 03:00 groups with multiplicity two; the demo
aggregate was unaffected, but the completed dependency full comparison has
8/73,181 endpoint conflicts. Resource ids are opaque and cannot recover the
original wall time. No terminal decision was made.

Artifacts:
- `mimic-iv/concepts_fhir/carryover/icustay_hourly/fhir-prober.md`
- `mimic-iv/concepts_fhir/carryover/icustay_hourly/carryover.json`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/icustay_hourly.md`
- Attempt: `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/`
