# FHIR mapping: `oxygen_delivery`

## Inputs and target shape

The source analyst identified one physical source table:

| MIMIC-IV source table | MIMIC-on-FHIR resource | Discriminator |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and exact `code.coding.code` |

The four source itemids are all present in the authoritative demo Delta as
chartevents Observations.  The code system is the chartevents system above, not
`mimic-d-items` and not a LOINC system.  `meta.profile` is not used as a
discriminator.

The full oracle manifest target is:

```text
subject_id                  INTEGER
stay_id                     INTEGER
charttime                   TIMESTAMP
o2_flow                     FLOAT
o2_flow_additional          FLOAT
o2_delivery_device_1        VARCHAR
o2_delivery_device_2        VARCHAR
o2_delivery_device_3        VARCHAR
o2_delivery_device_4        VARCHAR
```

It is a `keyed_join` comparison with natural key
`(subject_id, charttime)` and full-manifest row count 601,546.  `stay_id` is
not part of the key.

## Canonical source-column to FHIRPath mapping

The following paths are the columns to project from a canonical Observation
ViewDefinition.  The types in the last column are FHIR element types; a
Pathling materialized type is shown where it matters to the implementer.

| Source column / role | Canonical `{path, name}` | FHIR type and materialized type | Evidence / use |
|---|---|---|---|
| resource identity | `{"path": "getResourceKey()", "name": "observation_id"}` | resource key string; `StringType` | 4,393 targeted codings were 4,393 distinct Observation resources. Opaque identity only. |
| source `subject_id` join spine | `{"path": "subject.getReferenceKey(Patient)", "name": "patient_id"}` | Patient reference key string; `StringType` | 4,393/4,393 targeted rows populated. Join to Patient by equality, never parse the key. |
| source `subject_id` value | `{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}` on the Patient view | FHIR `Identifier.value` string; `StringType` | 4,393/4,393 linked target rows resolved to a subject identifier. Cast to manifest `INTEGER` only in outer SQL. |
| source `stay_id` join spine | `{"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id"}` | Encounter reference key string; `StringType` | 4,393/4,393 targeted rows populated. Join by equality only. |
| source `stay_id` value | `{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"}` on the Encounter view | FHIR `Identifier.value` string; `StringType` | 4,393/4,393 linked target rows resolved to a stay identifier. Cast to manifest `INTEGER` only in outer SQL. ICU Encounter stream selection is by this identifier system, not `Encounter.class`. |
| source `charttime` | `{"path": "(effective).ofType(dateTime)", "name": "effective_datetime"}` | FHIR `dateTime`; Pathling `StringType` | 4,393/4,393 targeted rows populated. Use `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` / `CAST(... AS TIMESTAMP_NTZ)` for manifest `charttime`; do not parse it as an instant or cast to ordinary `TIMESTAMP`. |
| unused choice check | `{"path": "(effective).ofType(Period).start", "name": "effective_period_start"}` | FHIR `dateTime`; Pathling `StringType` | 0/4,393 targeted rows populated. The chartevents ETL writes `effectiveDateTime`; this alias is not needed for this stream. |
| unused choice check | `{"path": "(effective).ofType(instant)", "name": "effective_instant"}` | FHIR `instant`; Pathling `TimestampType` | 0/4,393 targeted rows populated. Do not COALESCE this native timestamp with the dateTime string. |
| source `itemid` and filter code | inside `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')"`: `{"path": "code", "name": "code"}` | FHIR `Coding.code` string; `StringType` | Exact source itemid as text. Cast only after system filtering if an integer is needed. |
| code system | same constrained coding group: `{"path": "system", "name": "system"}` | FHIR `Coding.system` URI string; `StringType` | Exact system above. System + exact code is the discriminator. |
| dimension label (not a source SQL column) | same constrained coding group: `{"path": "display", "name": "display"}` | FHIR `Coding.display` string; `StringType` | Populated for all 4,393 target rows; useful for inspection only. The source query does not filter on labels. |
| flow `valuenum` | `{"path": "(value).ofType(Quantity).value", "name": "quantity_value"}` | FHIR `Quantity.value` decimal; Pathling ViewDefinition alias `StringType` | 1,248/1,248 demo flow rows populated (1,090 + 145 + 13). Cast to `DOUBLE` for flow output and ranking. |
| flow `valueuom` | `{"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"}` | FHIR `Quantity.unit` string; `StringType` | 1,248/1,248 demo flow rows populated with `L/min`; source `valueuom` agrees exactly. It is not in the final target shape. |
| device `value` | `{"path": "(value).ofType(string)", "name": "string_value"}` | FHIR `valueString` string; `StringType` | 3,145/3,145 item 226732 rows populated; source device text agrees exactly. `value.ofType(CodeableConcept)` is not the path. |
| source `storetime` | `{"path": "issued", "name": "issued"}` | FHIR `instant`; Pathling raw/materialized `TimestampType` | 4,393/4,393 populated. Readable issued wall time agrees with DuckDB source `storetime` 4,393/4,393 in the demo. Use this for both ranking windows. |
| Observation identifier probe | `forEachOrNull: "identifier"`, `{"path": "system", "name": "observation_identifier_system"}` and `{"path": "value", "name": "observation_identifier_value"}` | FHIR `Identifier.system`/`Identifier.value` strings | 0/4,393 populated for either column. No source oxygen-delivery field should be inferred from an Observation identifier. |

The source identifiers are therefore obtained through linked resources, not
from `getResourceKey()` or `getReferenceKey()`.  The implementer must retain
the `_str` and `_key` distinction and cast `subject_id_str` and `stay_id_str`
to the manifest integer types in the final projection.

## Exact coded filters and served counts

The source SQL names exactly `223834`, `227582`, `227287`, and `226732`.
The executable discriminator is system plus exact string code.  A constrained
coding group should be used rather than a bare unfiltered coding expansion:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')",
  "column": [
    {"path": "code", "name": "code"},
    {"path": "system", "name": "system"},
    {"path": "display", "name": "display"}
  ]
}
```

Authoritative demo Delta counts, after projecting `code.coding`, were:

| system | exact code | FHIR coding rows | distinct Observation resources | non-null patient key | non-null encounter key | non-null effective dateTime | non-null issued | non-null Quantity value | non-null valueString |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | `223834` | 1,090 | 1,090 | 1,090 | 1,090 | 1,090 | 1,090 | 1,090 | 0 |
| same | `227582` | 13 | 13 | 13 | 13 | 13 | 13 | 13 | 0 |
| same | `227287` | 145 | 145 | 145 | 145 | 145 | 145 | 145 | 0 |
| same | `226732` | 3,145 | 3,145 | 3,145 | 3,145 | 3,145 | 3,145 | 0 | 3,145 |

No lifted code was absent and no lifted code had a zero count.  All four have
the expected single system and exact code.  The coding expansion ratio is
`4,393 / 4,393 = 1.000` overall and is 1.000 for every code.  Thus the
constrained coding expansion does not multiply these demo rows; keep the
constraint nevertheless because the ratio is a warehouse property.

`mimic-d-items` is a different shared system used by outputevents and
datetimeevents.  It does not affect these four filters: the chartevents
system above is distinct, and within it the exact code is the source `d_items`
itemid.  Do not replace this rule with a profile predicate.

## Reproducing the source ranking and pivot

The FHIR rows are one row per Observation, including repeated observations at
one patient/time/item.  Do not deduplicate by `(stay_id, charttime, itemid)`
before ranking.  In the demo, the four code streams contained 4,393 source
rows and 4,393 FHIR rows.  For device code 226732 there were 3,145 rows in
3,014 `(subject_id, charttime)` groups; 106 groups had more than one row and
the maximum group size was 3.  This agrees with the established repeated
chartevents behavior.

### Flow branch

1. Filter `system` to the chartevents system and `code` to `223834`, `227582`,
   or `227287`.  The global chartevents ETL already removes source rows with
   NULL `value`; in the demo all 1,248 flow source values were non-NULL and
   all 1,248 had a Quantity.  To preserve the source inclusion rule if a
   future flow row has text but no numeric value, use resource presence / the
   equivalent `(quantity_value IS NOT NULL OR string_value IS NOT NULL)`, not
   Quantity alone.
2. Normalize the code with `CASE WHEN code IN ('223834','227582') THEN
   223834 ELSE CAST(code AS INTEGER) END`.  The two source codes compete in
   one normalized flow partition.
3. Cast `quantity_value` to `DOUBLE` as `valuenum`, retain `issued` as the
   `storetime` ordering column, and assign:

   ```text
   ROW_NUMBER() OVER (
     PARTITION BY subject_id, charttime, normalized_itemid
     ORDER BY issued DESC, quantity_value_numeric DESC
   )
   ```

   Keep only `rn = 1` before joining/pivoting.  Source `value` is not a
   secondary flow tie-breaker; the source orders by `storetime`, then
   `valuenum`.

### Device branch and final pivot

1. Filter to exact code `226732`; use `value.ofType(string)` as the device
   text and `issued` as `storetime`.
2. Rank by `(subject_id, charttime, itemid)` with

   ```text
   ROW_NUMBER() OVER (
     PARTITION BY subject_id, charttime, itemid
     ORDER BY issued DESC NULLS LAST, string_value DESC NULLS LAST
   )
   ```

   Only ranks 1 through 4 can reach the output columns.
3. Join the selected flow rows to device rows on `subject_id` and `charttime`
   only.  Do not add `stay_id` to this join.  The source's FULL OUTER JOIN is
   made flow-driven by `WHERE ce.rn = 1`, so a left join from selected flow
   rows reproduces the surviving semantics; device-only rows are excluded.
4. Group by `(subject_id, charttime)` only, use `MAX(stay_id)`, and pivot with
   `MAX(CASE ...)`:

   ```text
   MAX(CASE WHEN normalized_itemid = 223834 THEN quantity_value_numeric END)
       AS o2_flow
   MAX(CASE WHEN normalized_itemid = 227287 THEN quantity_value_numeric END)
       AS o2_flow_additional
   MAX(CASE WHEN device_rn = 1 THEN string_value END) AS o2_delivery_device_1
   MAX(CASE WHEN device_rn = 2 THEN string_value END) AS o2_delivery_device_2
   MAX(CASE WHEN device_rn = 3 THEN string_value END) AS o2_delivery_device_3
   MAX(CASE WHEN device_rn = 4 THEN string_value END) AS o2_delivery_device_4
   ```

   Output `charttime` is `CAST(effective_datetime AS TIMESTAMP_NTZ)`.  Keep
   the outer output timestamp as `TIMESTAMP_NTZ`, not Spark `TIMESTAMP`.

## Oracle checks

The read-only DuckDB oracle was `/Users/nau025/warehouses/mimic4-demo.db`.
For each of the four codes, source counts equaled the FHIR coding/resource
counts exactly:

```text
source rows by itemid:              223834=1090, 227582=13, 227287=145, 226732=3145
source value IS NOT NULL:           223834=1090, 227582=13, 227287=145, 226732=3145
source valuenum IS NOT NULL:        223834=1090, 227582=13, 227287=145, 226732=0
source storetime IS NOT NULL:       223834=1090, 227582=13, 227287=145, 226732=3145
source/FHIR tuple agreement:        4393/4393 exact
source/FHIR storetime agreement:    4393/4393 exact
```

The tuple check compared `(subject_id, stay_id, charttime, itemid, device
value, valuenum, valueuom, storetime)` after casting FHIR identifiers and
Quantity values and dropping the FHIR datetime offset as `TIMESTAMP_NTZ`.
The source labels and units also agreed: flow units were `L/min` for all 1,248
flow rows and device `valueuom` was NULL for all 3,145 device rows.

The source SQL pivot was independently replayed from the FHIR projections on
the demo.  Both produced 1,154 `(subject_id, charttime)` groups, with
1,154/1,154 key agreement and 1,154/1,154 value agreement for each of
`stay_id`, `o2_flow`, `o2_flow_additional`, and all four device slots.  A raw
pandas `DataFrame.equals` was false only because of dataframe dtype/null
representation; the keyed, null-normalized column comparisons were all
1,154/1,154.

The hard-coded global ETL exclusion tuple `(stay_id=34934165,
charttime='2151-10-03 05:14:00')` had 0 matching rows in the demo target item
set.  There were also 0 NULL `value` rows for each of the four itemids in the
demo.  These are coverage checks, not permission to use an Observation id as
a recovery mechanism.

## Gaps and essentiality

### `charttime`: absent exact source wall time at DST gaps — essential

`Observation.effectiveDateTime` is present and the direct mapping reproduced
the demo pivot, but the upstream chartevents ETL casts source `charttime`
through `TIMESTAMPTZ` before writing it.  A nonexistent New York spring-forward
02:xx wall time can therefore be served as 03:xx.  The original wall time is
not representable by any FHIR element.  It is not permissible to parse,
regenerate, compare, or invert `Observation.id` / `getResourceKey()` to recover
it.

This is potentially essential for `oxygen_delivery`: `charttime` is the
natural key, both window partitions use it, the flow/device join uses it, the
final group uses it, and a normalized 02:xx row can collide with a genuine
03:xx row.  That can change row inclusion, the selected flow, device ranks,
and all pivot slots.  The equivalence judge must assess the full concept; no
partial acceptance is made here.  The shared notes already document this
intrinsic transformation and its downstream aggregation effect.

### Numeric flow source `value` text: not retained, but non-essential here

When `valuenum` is non-NULL, the chartevents ETL writes only `valueQuantity`
and drops the original source text.  In this concept the flow branch uses
source `value` only for `value IS NOT NULL`; the FHIR resource's existence
preserves that inclusion, and flow selection uses `valuenum` plus `storetime`.
The exact numeric value and unit are present for all demo flow rows.  Therefore
the discarded raw text is an ancillary, absent-but-derivable inclusion witness
for this concept, not a final output column and not a measured source of
ambiguity in the demo.  It must not be recovered from the opaque resource id.

### Source NULL device rows: possible ETL coverage difference

The source `o2` CTE does not explicitly filter `value IS NOT NULL`, whereas the
global FHIR chartevents ETL does.  The demo has 0 NULL-valued rows for code
226732, so this did not change its rank or pivot.  If a full-data target
contains such a row, its omission could change device rank and is therefore a
potentially essential source loss; measure it in the full comparison rather
than inventing a NULL device resource.

### Observation identifier: absent, not needed for this grain

Observation `identifier` was NULL for all 4,393 targeted resources.  The
source output grain is `(subject_id, charttime)`, and the linked Patient and
ICU Encounter identifiers plus the Observation row cardinality provide all
fields needed by this concept.  The absence is not a source gap for the
declared output key.  Resource keys remain opaque identity only.

Two dataset-wide quirks were appended to
`MIMIC_NOTES.d/oxygen_delivery.md`: the verified `Observation.issued` to
chartevents `storetime` mapping and the verified repeated same-item
chartevents cardinality.  Other relevant findings (chartevents NULL-row
omission, categorical `valueString`, effective choice materialization,
identifier spine, itemid coding system, and DST normalization) were already
established in `MIMIC_NOTES.md` or verified in the fragments and were not
duplicated.

## Probe provenance

The embedded probe used Pathling 9.6.0 over
`/Users/nau025/warehouses/mimic-iv-demo/delta`, projected the ViewDefinition
paths above, and counted every mapped field as rows versus non-null rows.  The
probe output was retained during this run at
`/var/folders/yd/6k5p31n965n7pv46hvlw5sm40000gq/T/opencode/oxygen_probe6.txt`.
The canonical structural reference was
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
The source analysis input was
`mimic-iv/concepts_fhir/carryover/oxygen_delivery/source-analyst.md`.
