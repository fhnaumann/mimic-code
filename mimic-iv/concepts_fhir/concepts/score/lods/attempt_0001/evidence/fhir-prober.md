# FHIR-prober evidence — lods attempt_0001

The fhir-prober read the source-analysis carryover, canonical `lods.sql`,
dependency interfaces, `MIMIC_NOTES.md`, and relevant provisional fragments.
It probed the authoritative demo Delta with embedded Pathling 9.6.0/Spark
4.0.2 under UTC.

The ICU Encounter mapping was complete for the demo: 140/140 had ICU
identifier, `partOf`, patient reference, period start/end, and exact stay and
hospital identifiers. Patient identifiers were populated 100/100. CPAP input
item `226732` had 3,145 source/FHIR rows and 3,145 distinct resources; its
string value path was populated 3,145/3,145, with 4 CPAP and 28 BiPAP-mask
matches. It is dateTime-only (no Period/instant variant), and datetime strings
must be cast to `TIMESTAMP_NTZ`.

The six dependencies are consumed through their published key-shaped views,
using opaque equality joins rather than parsing IDs. The direct mapping is
ICU `Encounter` for the stay spine, parent hospital `Encounter` for `hadm_id`,
`Patient` for `subject_id`, and chartevents `Observation` code/value/effective
for the CPAP envelope. LODS and its components remain SQL-derived and retain
the source NULL semantics.

The probe independently confirmed the rebuilt numeric-chartevents component
repair for GCS: 9,791/9,791 selected resources had component text, including
1,348 `No Response-ETT` and 78 `No Response` values. It also identified that
the completed `first_day_gcs` dependency attempt_0002 predates that upstream
repair and carries an accepted divergence. This is inherited dependency state,
not a new LODS representability declaration; it must be passed to the judge.

Carryover was written to
`mimic-iv/concepts_fhir/carryover/lods/fhir-prober.md` and recorded. The
prober appended two dataset-wide findings to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/lods.md`:
rebuilt numeric chartevents preserve meaningful text in `component.valueString`,
and ICU chartevents effective timing is dateTime-only in the rebuilt Delta.
