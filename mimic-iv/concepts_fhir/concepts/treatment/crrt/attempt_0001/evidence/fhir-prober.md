## Evidence

The probe read `MIMIC_NOTES.md`, all existing notes fragments, the canonical
CRRT SQL, and the FHIR mapping guidance, then checked the authoritative demo
Delta with embedded Pathling/Spark against the demo DuckDB oracle. CRRT maps
from ICU chartevent Observations discriminated by
`code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'`
and exact string itemid; `meta.profile` is not used.

The identifier spine is Observation encounter reference → ICU Encounter
resource key → `Encounter.identifier` with system
`http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`; cast its string
value to INTEGER for `stay_id`. `Observation.effective.ofType(dateTime)` maps
to `charttime` and must be cast to `TIMESTAMP_NTZ`. Numeric values use
`(value).ofType(Quantity).value` and require numeric casting; string values use
`(value).ofType(string)`. The probe found no usable Period or instant variant.

All 7,347 filtered demo source rows matched 7,347 targeted FHIR Observations
for every present itemid, value, unit, and ICU stay. Item 225958 was absent in
the demo. Item 224146 has repeated observations at one stay/time, so the SQL
must preserve observations before pivoting. Sixteen demo charttimes at
stay_id 30932571 were shifted from source 02:00 to FHIR 03:00 by the known DST
gap transformation; this is already recorded in `MIMIC_NOTES.md`.

The probe corrected the source-stage count: the target has 14 numeric measures,
4 string measures (`crrt_mode`, `dialysate_fluid`, `heparin_concentration`,
`replacement_fluid`), and 4 integer flags. It wrote the reusable mapping to
`mimic-iv/concepts_fhir/carryover/crrt/fhir-prober.md` and appended the
dataset-wide repeated-observation finding to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/crrt.md`.
