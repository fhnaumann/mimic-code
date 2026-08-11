# FHIR prober mapping — crrt

## Source resource and discriminator

`mimiciv_icu.chartevents` maps to the merged FHIR `Observation` resource.
The authoritative demo Delta is `/Users/nau025/warehouses/mimic-iv-demo/delta`;
the DuckDB oracle used for source checks is
`/Users/nau025/warehouses/mimic4-demo.db`.

Filter the repeated coding inside the ViewDefinition, rather than using
`meta.profile`:

```text
forEach: code.coding.where(
  system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
)
```

The coding system was observed on all 7,347 targeted Observation codings.  The
code is the source `chartevents.itemid` as an unmodified decimal string and
`display` is the d-items label.  There was exactly one coding per targeted
Observation (7,347 coding rows / 7,347 distinct resources = 1.0), so the
constrained `forEach` does not fan out.  The exact system plus code is the
discriminator; `meta.profile` is not used.

## Canonical Observation extraction

These are the canonical columns the implementer should project from
`Observation` (the resource/reference keys are UUID strings and are not output
`stay_id` values):

| FHIRPath | name | FHIR/materialized type | Probe result |
|---|---|---|---|
| `getResourceKey()` | `observation_id` | string / VARCHAR | 7,347/7,347 non-null; UUID resource key |
| `subject.getReferenceKey(Patient)` | `patient_id` | string / VARCHAR | 7,347/7,347 non-null |
| `encounter.getReferenceKey(Encounter)` | `encounter_id` | string / VARCHAR | 7,347/7,347 non-null |
| `(effective).ofType(dateTime)` | `effective_datetime` | FHIR dateTime, materialized VARCHAR | 7,347/7,347 non-null; offset-bearing ISO strings |
| `(effective).ofType(Period).start` | `effective_period_start` | dateTime-like VARCHAR | 0/7,347; do not rely on this variant |
| `(effective).ofType(instant)` | `effective_instant` | native Spark timestamp | 0/7,347; omit from this view |
| `(value).ofType(Quantity).value` | `quantity_value` | FHIR decimal, materialized VARCHAR | 5,720/7,347 non-null |
| `(value).ofType(Quantity).unit` | `quantity_unit` | string / VARCHAR | 5,720/7,347 non-null |
| `(value).ofType(Quantity).comparator` | `quantity_comparator` | string / VARCHAR | 0/7,347 non-null |
| `(value).ofType(string)` | `string_value` | string / VARCHAR | 1,627/7,347 non-null |
| `code` inside the coding `forEach` | `code` | string / VARCHAR | 7,347/7,347 non-null for present codes |
| `system` inside the coding `forEach` | `system` | string / VARCHAR | 7,347/7,347 non-null |
| `display` inside the coding `forEach` | `display` | string / VARCHAR | 7,347/7,347 non-null |

`quantity_value` and `quantity_unit` are string-like ViewDefinition aliases in
Pathling 9.6.0.  The implementer must cast the numeric aliases to the manifest's
numeric type in the outer SQL; a VARCHAR alias is not a finished numeric
output.  Datetimes must be cast to `TIMESTAMP_NTZ`, not plain `TIMESTAMP`, and
the outermost type must remain `TIMESTAMP_NTZ`.

The ICU stay join is:

```text
Observation.encounter.getReferenceKey(Encounter)
  -> Encounter.getResourceKey()
  -> Encounter.identifier.where(
       system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
     ).value
```

The identifier value is a FHIR string (`stay_id_str`); cast it to the oracle's
integer `stay_id` only in the final SQL.  All 7,347 target observations joined
to an ICU Encounter identifier and all 7,347 subject and encounter references
were non-null.  A Patient join is available through `patient_id`, but crrt's
source output does not contain `subject_id` and does not need to emit it.

## Itemid/value mapping

All itemid filters below use the canonical `code` alias as the exact string code in the
chartevents-d-items system above.  Numeric source `valuenum` maps to
`(value).ofType(Quantity).value`; source `valueuom` maps to
`(value).ofType(Quantity).unit`.  String source `value` maps to
`(value).ofType(string)`.  The FHIR type is the type of the extracted FHIR
element; the materialized aliases are VARCHAR unless noted above.

| Source output / source itemid | FHIR `{path, name}` | FHIR type; observed demo rows | Confirmed values/units |
|---|---|---|---|
| `stay_id` | `{path: identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value, name: stay_id_str}` on the joined `Encounter` view; join with `{path: encounter.getReferenceKey(Encounter), name: encounter_id}` | string / VARCHAR, final output INTEGER | 7,347 Observation rows joined to ICU Encounter identifiers |
| `charttime` | `{path: (effective).ofType(dateTime), name: effective_datetime}` | dateTime / VARCHAR alias, final output TIMESTAMP_NTZ | 7,347/7,347 populated |
| `crrt_mode` / itemid `227290` | `{path: (value).ofType(string), name: string_value}` with `{path: code, name: code}` filter `227290` | string / VARCHAR | `CVVHDF`: 217/217; Quantity 0/217 |
| `access_pressure` / `224149` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 426/426 Quantity; unit `mmHg` 426/426 |
| `blood_flow` / `224144` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 435/435 Quantity; unit `ml/min` 435/435 |
| `citrate` / `228004` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 275/275 Quantity; unit `ml/hr` 275/275 |
| `current_goal` / `225183` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 442/442 Quantity; unit `mL` 442/442 |
| `dialysate_fluid` / `225977` | `{path: (value).ofType(string), name: string_value}` | string / VARCHAR | `Prismasate K2` 211, `Prismasate K4` 228; 439 total |
| `dialysate_rate` / `224154` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 440/440 Quantity; unit `ml/hr` 440/440 |
| `effluent_pressure` / `224151` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 425/425 Quantity; unit `mmHg` 425/425 |
| `filter_pressure` / `224150` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 426/426 Quantity; unit `mmHg` 426/426 |
| `heparin_concentration` / `225958` | `{path: (value).ofType(string), name: string_value}` | string / VARCHAR | source total/non-null 0/0 and FHIR 0 rows in demo; listed code is absent, not evidence of a general full-data omission |
| `heparin_dose` / `224145` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 217/217 Quantity; unit `units` 217/217 |
| `hourly_patient_fluid_removal` / `224191` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 449/449 Quantity; unit `mL` 449/449 |
| `prefilter_replacement_rate` / `228005` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 440/440 Quantity; unit `ml/hr` 440/440 |
| `postfilter_replacement_rate` / `228006` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 439/439 Quantity; unit `ml/hr` 439/439 |
| `replacement_fluid` / `225976` | `{path: (value).ofType(string), name: string_value}` | string / VARCHAR | `Prismasate K2` 304, `Prismasate K4` 135; 439 total |
| `replacement_rate` / `224153` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 440/440 Quantity; unit `ml/hr` 440/440 |
| `return_pressure` / `224152` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 425/425 Quantity; unit `mmHg` 425/425 |
| `ultrafiltrate_output` / `226457` | `{path: (value).ofType(Quantity).value, name: quantity_value}` plus `{path: (value).ofType(Quantity).unit, name: quantity_unit}` | decimal materialized VARCHAR; unit string | 441/441 Quantity; unit `mL` 441/441 |
| `system_active` / `224146` | `{path: (value).ofType(string), name: string_value}` | string source; final integer flag | `Active`/`Initiated`/`Reinitiated`/`New Filter` → 1; `Recirculating`/`Discontinued` → 0 |
| `clots` / `224146` | `{path: (value).ofType(string), name: string_value}` | string source; final integer flag | `Clots Present` → 1; `No Clot Present` → 0 |
| `clots_increasing` / `224146` | `{path: (value).ofType(string), name: string_value}` | string source; final integer flag | `Clots Increasing` or `Clot Increasing` → 1; the demo has `Clots Increasing` 1 row and no `Clot Increasing` row |
| `clotted` / `224146` | `{path: (value).ofType(string), name: string_value}` | string source; final integer flag | `Clotted` → 1 |

The four source `ce.value` outputs are `crrt_mode`, `dialysate_fluid`,
`heparin_concentration`, and `replacement_fluid`; the source-analyst summary
under-counted these as three VARCHAR measures.  There are 14 numeric measures,
4 string measures, and 4 integer flags.

## Counts, duplicates, and transformations

DuckDB source counts (`value IS NOT NULL`) and Delta/FHIR counts agree exactly
for every present itemid:

```text
itemid  source total/non-null  FHIR rows
224144  435/435               435
224145  217/217               217
224146  532/532               532
224149  426/426               426
224150  426/426               426
224151  425/425               425
224152  425/425               425
224153  440/440               440
224154  440/440               440
224191  449/449               449
225183  442/442               442
225976  439/439               439
225977  439/439               439
226457  441/441               441
227290  217/217               217
228004  275/275               275
228005  440/440               440
228006  439/439               439
225958  0/0                   0
```

The source has 7,347 filtered rows, 580 distinct `(stay_id, charttime)` keys,
and 7,250 distinct `(stay_id, charttime, itemid)` keys.  Item `224146` is not
unique at a stay/time: its source multiplicity is 338 keys with one row, 94
keys with two rows, and 2 keys with three rows.  FHIR preserves all 532
Observations.  The implementer must therefore pivot the observations only
after preserving the repeated 224146 values; do not assume one row per
stay/time/item.

The 7,347 source/FHIR tuples agreed exactly on ICU stay, itemid, value, and
unit when the time field was ignored (7,347/7,347).  Including effective wall
time, 7,331/7,347 tuples agreed; 16 source Observation rows at
`stay_id=30932571`, source `charttime=2116-03-08 02:00:00`, were serialized by
the FHIR ETL at `effectiveDateTime=2116-03-08T03:00:00-04:00` due to the
upstream DST-gap normalization.  This is the established dataset-wide
datetime transformation in `MIMIC_NOTES.md`, not a CRRT-specific value or
code mapping.  The demo's chartevents ETL `value IS NOT NULL` behavior caused
no additional CRRT omission: source and FHIR counts were 7,347 each.  The
generic hard-coded duplicate exclusion at
`mimic-fhir/sql/fhir_observation_chartevents.sql:34-37` was not exercised by
the demo CRRT rows.

The full oracle manifest reports 287,152 final crrt rows at `(stay_id,
charttime)`; the probes above are the authoritative 100-patient demo counts.
