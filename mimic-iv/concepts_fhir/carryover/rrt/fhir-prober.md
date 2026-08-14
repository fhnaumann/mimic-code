# FHIR mapping: `rrt`

## Authority and probe basis

The source specification is `mimic-iv/concepts/treatment/rrt.sql`.  The
authoritative served-data probe used embedded Pathling 9.6.0 over
`/Users/nau025/warehouses/mimic-iv-demo/delta`; no raw `Mimic*.ndjson.gz` was
used.  The source-side checks used the read-only DuckDB oracle
`/Users/nau025/warehouses/mimic4-demo.db`.

The canonical ViewDefinition shape was checked against
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
The output manifest says that `rrt` has columns
`stay_id INTEGER`, `charttime TIMESTAMP`, `dialysis_present INTEGER`,
`dialysis_active INTEGER`, and `dialysis_type VARCHAR`, with
`full_tuple_multiset` comparison and no declared key.  The semantic coordinate
is `(stay_id, charttime)`, but it is not unique: the implementer must preserve
multiset cardinality and must not use a FHIR resource id as a source key.

The shared notes that changed this mapping decision were:

- `MIMIC_NOTES.md` identifier spine: MIMIC ids are `identifier.value` strings;
  `getResourceKey()` and `getReferenceKey()` are opaque UUID join keys.
- `MIMIC_NOTES.md` Observation subtype and coding rules: discriminate on
  `code.coding.system` plus exact `code`, never `meta.profile`; itemids are
  verbatim codes.
- `MIMIC_NOTES.md` categorical chartevents rule: text values are
  `Observation.value.ofType(string)`, not a CodeableConcept.
- `MIMIC_NOTES.md` polymorphic/datetime rules: project every choice variant;
  FHIR datetime strings must be cast to `TIMESTAMP_NTZ` in Spark, not parsed as
  instants in the machine timezone.
- `MIMIC_NOTES.md` DST rule: an upstream spring-forward normalization can make
  FHIR effective/performed wall time differ from the source by one hour.  Do
  not attempt to recover it from an opaque resource id.

The provisional fragments read were `MIMIC_NOTES.d/crrt.md`,
`MIMIC_NOTES.d/oxygen_delivery.md`, `MIMIC_NOTES.d/gcs.md`, and
`MIMIC_NOTES.d/icustay_times.md`.  Their repeated-chartevent and value-choice
leads were checked against the RRT Delta probe; their UUID-recovery claims
were **not** adopted, and the DST aggregation lead was not independently
tested in this mapping run.

## Resource/table mapping

| Source table/role | Served FHIR resource | Resource evidence and join |
|---|---|---|
| `mimiciv_icu.chartevents` (`ce`) | `Observation` (`mimic-observation-chartevents`) | RRT code filter over the chartevents coding system produced 8,480 rows/resources. `Observation.encounter` references an ICU `Encounter`; `Observation.subject` references `Patient`. |
| `mimiciv_icu.inputevents` (`mv_ranges` first branch) | `MedicationAdministration` (ICU input stream) | The two source itemids are medication codings in `medication.ofType(CodeableConcept).coding` under `mimic-medication-icu`. `context` references the ICU `Encounter`; `subject` references `Patient`. |
| `mimiciv_icu.procedureevents` (`mv_ranges` second branch) | `Procedure` (ICU procedure stream) | The eight source itemids are `Procedure.code.coding` values under `mimic-d-items`. `Procedure.encounter` references the ICU `Encounter`; `subject` references `Patient`. |
| ICU stay lookup for all three streams | `Encounter` filtered to `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | `Encounter.getResourceKey()` joins the resource/reference key from each event. The relational `stay_id` is `identifier.value`, projected as a string and cast to `INTEGER` only in the derived SQL. |
| subject lookup for all three streams | `Patient` | `Patient.getResourceKey()` joins `subject.getReferenceKey(Patient)`. If a numeric subject id is needed, use `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value` and cast it; RRT does not emit `subject_id`. |

## Canonical ViewDefinition projections

These are mapping specifications, not attempt implementation files.  Keep the
`*_key` and `*_str` aliases in the FHIR views; cast the identifier strings in
the final SQL.  Coded filters belong inside `forEach`.

### ICU Encounter identifier view

Resource: `Encounter`; FHIR types are `string` for `identifier.value` and
opaque `string` for the Pathling resource key.

```json
{
  "path": "getResourceKey()",
  "name": "encounter_key"
}
{
  "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
  "column": [
    { "path": "value", "name": "stay_id_str" }
  ]
}
```

The derived SQL equivalent is `CAST(stay_id_str AS INTEGER) AS stay_id`.
Never parse `encounter_key` or look up a guessed UUID.

### Observation view for `chartevents`

Resource: `Observation`.  The FHIR choice type is `Observation.effective[x]`
intentional.

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "observation_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
    { "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" },
    { "path": "(value).ofType(string)", "name": "string_value" },
    { "path": "issued", "name": "issued" }
  ]
}
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='226118' or code='227357' or code='225725' or code='226499' or code='224154' or code='225810' or code='227639' or code='225183' or code='227438' or code='224191' or code='225806' or code='225807' or code='228004' or code='228005' or code='228006' or code='224144' or code='224145' or code='224149' or code='224150' or code='224151' or code='224152' or code='224153' or code='224404' or code='224406' or code='226457' or code='225959' or code='224135' or code='224139' or code='224146' or code='225323' or code='225740' or code='225776' or code='225951' or code='225952' or code='225953' or code='225954' or code='225956' or code='225958' or code='225961' or code='225963' or code='225965' or code='225976' or code='225977' or code='227124' or code='227290' or code='227638' or code='227640' or code='227753'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

FHIR types: `observation_key`, `patient_key`, and `encounter_key` are opaque
Pathling `string` identities; `effective_datetime`/period endpoints are FHIR
`dateTime`/`Period` values materialized as strings; `quantity_value` is a FHIR
`decimal` but Pathling ViewDefinition output is string-like and must be cast
before numeric use; `quantity_unit`, `string_value`, `issued`, and coding
columns are string-like (`issued` is FHIR `instant`); coding code/system/display
are strings.

Source-to-path mapping for `ce`:

| Source field/filter | FHIRPath / canonical `{path, name}` | FHIR type and use |
|---|---|---|
| `ce.stay_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` joined to `{ "path": "value", "name": "stay_id_str" }` from ICU Encounter identifier | Reference/resource key is opaque `string`; identifier value is FHIR `string`, final target `INTEGER`. Equality join, never id parsing. |
| `ce.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | FHIR `dateTime`, materialized string; final target `TIMESTAMP`, using `CAST(... AS TIMESTAMP_NTZ)`. |
| `ce.itemid` | `forEach: code.coding.where(system=chartevents-system and exact source code)`; `{ "path": "code", "name": "item_code" }` | FHIR `Coding.code` string; `CAST(item_code AS INTEGER)` recovers itemid. |
| `ce.value IS NOT NULL` | Resource existence after the exact code `forEach`; inspect `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` and `{ "path": "(value).ofType(string)", "name": "string_value" }` | The source predicate is a row filter, not an output value. Demo target count is 8,480, with no selected source NULL values. |
| `ce.value` for `itemid=225965` and `value='In use'` | `{ "path": "(value).ofType(string)", "name": "string_value" }`, with code `225965` | FHIR `string`; this exact discriminator was not populated in the demo (0 rows for 225965), so retain the code-plus-string predicate for full data. |
| `ce.value` for `itemid=227290` | `{ "path": "(value).ofType(string)", "name": "string_value" }`, with code `227290` | FHIR `string`; the RRT demo has 217/217 string values and the raw mode value is preserved. |
| `ce.value` on numeric rows | Quantity variant `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` identifies the row, but the original text is not a FHIR path when `valuenum` was non-null | The source text is not representable on 6,328 demo rows, but RRT does not use its numeric text, only non-nullness; this is not an essential loss for the RRT outputs. |
| `dialysis_present` chart CASE | Exact code membership in the `forEach`; emit literal `1` for the 48 selected codes, then retain only `dialysis_present=1` | Derived `INTEGER`; no terminology translation. |
| `dialysis_active` chart CASE | Code `225965` plus `string_value='In use'`, or code membership in the 14 active numeric codes | Derived `INTEGER`; the code survives and the text variant survives where present. |
| `dialysis_type` chart CASE | Code `227290` + `string_value`; PD code membership → `'Peritoneal'`; code `226499` → `'IHD'`; otherwise NULL | Derived nullable `VARCHAR`; `227290` is not translated. |
| `ce.storetime` | Optional `{ "path": "issued", "name": "issued" }` | FHIR `instant`; not referenced by source RRT SQL. The RRT Delta probe found it populated 8,480/8,480. |

The chart item list is exactly the source's 48 unique itemids.  The source
contains `225810` twice in the PD `CASE`; the FHIR filter must list it once,
because duplicate Boolean disjuncts do not change membership.

### MedicationAdministration view for `inputevents`

Resource: `MedicationAdministration`.  ICU `inputevents` are not an
Observation stream and must not be filtered using the chartevents coding
system.

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "medadmin_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "context.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
    { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
    { "path": "(effective).ofType(Period).end", "name": "effective_period_end" },
    { "path": "(dosage.dose).ofType(Quantity).value", "name": "dose_value" },
    { "path": "(dosage.dose).ofType(Quantity).unit", "name": "dose_unit" },
    { "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" },
    { "path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit" }
  ]
}
{
  "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and (code='227536' or code='227525'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

FHIR types: keys and references are opaque `string`; effective variants are
FHIR `dateTime`/`Period` strings; dose/rate values are FHIR `decimal` aliases
(cast before numeric arithmetic), units and coding fields are strings.

| Source field/filter | FHIRPath / canonical `{path, name}` | FHIR type and use |
|---|---|---|
| `ie.stay_id` | `{ "path": "context.getReferenceKey(Encounter)", "name": "encounter_key" }` → ICU Encounter identifier `{ "path": "value", "name": "stay_id_str" }` | Opaque reference `string` plus identifier `string`, final target `INTEGER`. `MedicationAdministration` uses `context`, not `encounter`. |
| `ie.starttime` | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | FHIR `Period.start`, materialized string; final target `TIMESTAMP_NTZ`. |
| `ie.endtime` | `{ "path": "(effective).ofType(Period).end", "name": "effective_period_end" }` | FHIR `Period.end`, materialized string; final target `TIMESTAMP_NTZ`. |
| `ie.itemid` | Medication coding `forEach` above; `{ "path": "code", "name": "item_code" }` | FHIR `Coding.code` string; exact codes `227536` and `227525`; final filter uses `CAST(item_code AS INTEGER)`. The source SQL comment says `227525` (the analyst's prose briefly contained `225525`); Delta confirms `227525`, not `225525`. |
| `ie.amount > 0` | `{ "path": "(dosage.dose).ofType(Quantity).value", "name": "dose_value" }` | FHIR `Quantity.value` decimal/string alias. Demo: 174/174 dose values populated; source and FHIR interval rows agree, with ordinary decimal serialization precision differences. |
| `ie.amount` | Same dose Quantity value path | Its magnitude is not otherwise transformed by RRT; it is the input inclusion predicate. |
| `ie.rate` | `{ "path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value" }` | Not referenced by RRT SQL, but the upstream ETL uses rate-nullness to choose `effectivePeriod` versus `effectiveDateTime`. Demo target rows: rate 174/174; dateTime 0/174 and Period start/end 174/174. |
| Input branch constants | No FHIR path; derive `dialysis_present=1`, `dialysis_active=1`, `dialysis_type='CRRT'` for the two exact medication codes | Derived `INTEGER`, `INTEGER`, nullable `VARCHAR`. |
| `ie.orderid` | No source-value FHIR element; it contributes only to upstream resource identity | Not representable as a mapped clinical field. Do not parse or regenerate `medadmin_key`; RRT has no declared natural key and must preserve resource cardinality. |

Important bounded gap: if a full-data target row satisfying `amount > 0` has
`rate IS NULL`, the ICU medication ETL writes only `effectiveDateTime` (the
source end time), so source `starttime` is absent and cannot be derived from
that dateTime. In the authoritative demo this reaches 0/174 rows. It would be
essential on exactly the affected rows because starttime controls the interval
start row and inclusive overlay; the implementer should emit typed NULL for
the unavailable start only if the surviving discriminator is sufficient, and
the judge should assess any full-data occurrence rather than reconstructing an
interval from an opaque id.

### Procedure view for `procedureevents`

Resource: `Procedure`.  The served ICU procedure ETL uses `performedPeriod`.
Project both `performed[x]` variants anyway, because choice fields are not
safe to assume single-typed across warehouse variants.

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "procedure_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
    { "path": "(performed).ofType(dateTime)", "name": "performed_datetime" },
    { "path": "(performed).ofType(Period).start", "name": "performed_period_start" },
    { "path": "(performed).ofType(Period).end", "name": "performed_period_end" }
  ]
}
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items' and (code='225441' or code='225802' or code='225803' or code='225805' or code='224270' or code='225809' or code='225955' or code='225436'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

| Source field/filter | FHIRPath / canonical `{path, name}` | FHIR type and use |
|---|---|---|
| `pe.stay_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` → ICU Encounter identifier value `{ "path": "value", "name": "stay_id_str" }` | Reference key and identifier are strings; final target `INTEGER`. |
| `pe.starttime` | `{ "path": "(performed).ofType(Period).start", "name": "performed_period_start" }` | FHIR `Period.start` string; final target `TIMESTAMP_NTZ`. |
| `pe.endtime` | `{ "path": "(performed).ofType(Period).end", "name": "performed_period_end" }` | FHIR `Period.end` string; final target `TIMESTAMP_NTZ`. |
| `pe.itemid` | Procedure code `forEach` above; `{ "path": "code", "name": "item_code" }` | FHIR `Coding.code` string under `mimic-d-items`; exact code plus system is the discriminator. This system is shared with output/datetime streams, but `d_items.itemid` is a global PK with one `linksto`, so these exact procedure codes identify the procedure stream without `meta.profile`. |
| `pe.value IS NOT NULL` | Procedure resource existence after exact code filtering | Source `value` magnitude has no FHIR equivalent. The predicate is preserved by the ETL's existence of the resource; demo source and FHIR both have 30 included rows. Zero and negative values pass the source predicate but are not output. |
| `pe.orderid` | No source-value FHIR element; contributes only to upstream resource identity | Not representable as a mapped clinical field. Resource identity is opaque and must not be parsed. |
| `pe.statusdescription` | No RRT use; ETL may populate `Procedure.status` | Not needed by this concept and not a source RRT output. |
| `pe.location`, `pe.ordercategoryname` | No RRT use; ETL may populate `Procedure.bodySite` / `category` | Not needed by this concept. |
| Procedure interval constants | Code mapping: `225441→'IHD'`, `225802→'CRRT'`, `225803→'CVVHD'`, `225805→'Peritoneal'`, `225809→'CVVHDF'`, `225955→'SCUF'`; `224270` and `225436` active=0/type=NULL; all present=1 | Derived `INTEGER`, `INTEGER`, nullable `VARCHAR`. |

## Literal code confirmation from Delta

The system was established by projecting the coding element inside the
filtered `forEach`, not from the table name or stale NDJSON.  All observed
codings had exactly one coding per resource in each filtered stream.

### Chartevents codes

System for every row: `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.
Counts are `Delta rows/resources`:

```text
224144 435/435   224145 217/217   224146 532/532   224149 426/426
224150 426/426   224151 425/425   224152 425/425   224153 440/440
224154 440/440   224191 449/449   224404 119/119   224406 119/119
225183 442/442   225323 177/177   225725 12/12     225740 1/1
225956 2/2       225976 439/439   225977 439/439   226118 175/175
226457 441/441   226499 10/10     227124 172/172   227290 217/217
227357 173/173   227753 173/173   228004 275/275   228005 440/440
228006 439/439
```

The following source-listed chart codes had zero rows in the demo Delta (not
silently removed from the filter):

```text
224135, 224139, 225810, 225806, 225807, 225776, 225951, 225952,
225953, 225954, 225958, 225959, 225961, 225963, 225965, 227438,
227639, 227638, 227640
```

The filtered Observation totals were 8,480 rows/resources; 8,480/8,480 had
patient reference, encounter reference, effective dateTime, issued, code,
system, and display.  `effective_period_start` was 0/8,480.  Quantity value
was 6,328/8,480, Quantity unit 5,968/8,480, and string value 2,152/8,480.
The coding cardinality ratio was `8,480 / 8,480 distinct Observation keys =
1.000`.

### Inputevents codes

System for every row:
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`.

```text
227536 105/105
227525  69/69
```

The source analyst's executable SQL has `227525`; a separate accidental probe
of `225525` found no Delta input rows and no served coding.  `225525` is not a
RRT code and must not enter the ViewDefinition filter.

The filtered MedicationAdministration totals were 174 rows/resources.
Patient reference, context/Encounter reference, Period start, Period end,
dose value, and rate value were each 174/174; effective dateTime was 0/174.
The coding cardinality ratio was `174 / 174 = 1.000`.

### Procedureevents codes

System for every row:
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`.

```text
224270 8/8     225436 2/2     225441 7/7     225802 13/13
225803 0/0     225805 0/0     225809 0/0     225955 0/0
```

The filtered Procedure totals were 30 rows/resources.  Patient reference,
encounter reference, performed Period start, and performed Period end were
each 30/30; performed dateTime was 0/30.  The coding cardinality ratio was
`30 / 30 = 1.000`.

The exact system-plus-code discriminator is warranted for the procedure
stream even though `mimic-d-items` is also used by `outputevents` and
`datetimeevents`: `d_items.itemid` is a global primary key with one
`linksto` value per item, and the exact RRT procedure itemids are the
procedureevents items.  The rule would need rechecking if a future data
preparation reused an itemid across streams.  `meta.profile` is not used.

## Source/oracle checks

Read-only checks against `mimic4-demo.db` and Delta gave:

- Chart source selected rows (`itemid IN (48 codes) AND value IS NOT NULL`):
  8,480; filtered Observation resources: 8,480.  The probe found one
  Observation per resource and confirmed all 48 code predicates against the
  served system.  A coordinate comparison on `(stay_id,itemid,charttime)`
  matched 8,464/8,480 rows; 16 source/FHIR coordinate differences are
  consistent with the established upstream datetime/resource preparation
  behavior and must not be repaired by id recovery.  The served-resource
  count and per-code counts are the authoritative mapping evidence.
- Input source rows (`itemid IN (227536,227525) AND amount > 0`): 174; FHIR
  MedicationAdministration resources: 174.  All 174 have the Period variant
  in the demo.  Interval coordinates matched the source; decimal materialized
  values show ordinary floating/decimal serialization differences, so the
  implementer must cast the FHIR Quantity alias before numeric comparison.
- Procedure source rows (`itemid IN (eight codes) AND value IS NOT NULL`):
  30; FHIR Procedure resources: 30.  The `(stay_id,itemid,starttime,endtime)`
  interval comparison was 30/30 exact.
- A read-only reconstruction of the source RRT overlay using the three
  mappings produced 5,124 candidate rows versus 5,134 oracle rows; every
  candidate tuple was in the oracle multiset and the only residual was 10
  oracle-only tuples.  The output is unkeyed by the manifest, so this is
  evidence for mapping/cardinality, not a convergence verdict.
- A focused repeated-row check for chart item `224146` found 532 source rows
  and 532 FHIR resources, with 434 `(stay_id, charttime)` groups, 96 repeated
  groups, and maximum group size 3 in the Delta probe.  This independently
  confirms that the RRT mapping must not deduplicate chartevents by stay/time.

## Gaps and representability

1. **Chart `value` on numeric rows — absent but nonessential for RRT.** The
   source text is discarded when FHIR writes `valueQuantity`; in this probe
   6,328/8,480 rows were Quantity and 2,152/8,480 were string.  RRT uses
   numeric-row `value` only for non-null inclusion, and uses the surviving
   string for the `225965`/`227290` branches.  The surviving code and value
   variant identify the affected rows, so this is a bounded typed-NULL/value
   gap, not a whole-concept block.  Resource ids are not a permitted side
   channel.
 2. **Procedure `value` — potentially essential and not representable if NULL
    rows exist.** The served `Procedure` preserves the exact code and performed
    interval but not `procedureevents.value`.  RRT uses `value IS NOT NULL` for
    row inclusion.  The demo has 30/30 selected source rows non-NULL and 30/30
    FHIR resources, so the measured demo loss is 0 rows.  If full data has
    NULL-valued selected procedures, no surviving FHIR discriminator identifies
    those omitted rows; this can change row multiplicity and warrants whole-
    concept blocking by the judge.  Do not infer it from an opaque id.
 3. **Input starttime where ETL chooses `effectiveDateTime` — bounded,
    potentially essential, not observed in demo.** The FHIR ETL's rate
    discriminator can omit the source start when rate is NULL.  The demo has
    0/174 such rows and 174/174 Periods, so no measured demo loss exists.  On
    affected full-data rows, the missing start reaches interval-start output
    and inclusive range matching; emit a typed NULL for the unavailable start
    and do not infer it from an id.  The judge must bound that row-level loss.
 4. **Upstream DST wall-time normalization — not representable on affected
   timestamps.** `Observation.effectiveDateTime`, MedicationAdministration
   Period endpoints, and Procedure performed endpoints can be normalized by
   the upstream ETL.  This can alter interval equality and output row
   multiplicity on affected rows.  The loss is a de-identification/ETL time
   transform; resource ids are opaque and cannot recover the source time.
   Cast served strings to `TIMESTAMP_NTZ` to avoid adding a second timezone
   conversion.  The equivalence judge must bound any full-data residual.

No new dataset-wide quirk was appended to `MIMIC_NOTES.d/rrt.md`: the RRT
probe verified the already-known chartevents code/value/cardinality rules but
did not establish a new rule independent of this concept.  No attempt
implementation file was authored.
