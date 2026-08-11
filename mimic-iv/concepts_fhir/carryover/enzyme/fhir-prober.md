# FHIR prober mapping: `enzyme`

## Scope and source of truth

- Source concept: `mimic-iv/concepts/measurement/enzyme.sql`.
- Source table: `mimiciv_hosp.labevents` (`subject_id`, `hadm_id`,
  `charttime`, `specimen_id`, `itemid`, and `valuenum`).
- FHIR warehouse probed: `/Users/nau025/warehouses/mimic-iv-demo/delta`, using
  Pathling 9.6.0 embedded on Spark 4.0.2. The HTTP Pathling server was not
  used.
- Oracle probed read-only at `/Users/nau025/warehouses/mimic4-demo.db`.
- Full target shape from
  `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`: 1,639,514 rows,
  key `specimen_id`, with `subject_id` INTEGER, `hadm_id` INTEGER,
  `charttime` TIMESTAMP, `specimen_id` INTEGER, and all eleven analytes DOUBLE.

The FHIR resource mapping is:

| Source relation/role | FHIR resource | Reason |
|---|---|---|
| `labevents` measurement row | `Observation` | Lab observations carry the item code, Quantity/string value, effective time, patient, encounter, and specimen references. |
| `labevents.specimen_id` grouping key | `Specimen` | The lab specimen identifier is preserved in `Specimen.identifier`; the resource is the grouping spine. |
| `subject_id` identifier | `Patient` | The MIMIC subject id is in the Patient identifier, not the resource UUID. |
| `hadm_id` identifier | `Encounter` | Hospital admission ids are in the hospital Encounter identifier; the Observation encounter reference is incomplete. |

`d_labitems` is not a source-table dependency of the concept. The FHIR ETL
uses it only to populate the Observation coding display and the Specimen type;
the filter remains the literal source itemid set.

## Canonical ViewDefinition columns

These are the exact select-column shapes to carry into the implementation. All
FHIR identifier values and materialized choice aliases below are strings. The
outer concept SQL must cast the numeric identifier/value aliases to the
manifest types.

Observation base group:

```json
[
  { "path": "getResourceKey()", "name": "observation_key" },
  { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
  { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
  { "path": "specimen.getReferenceKey(Specimen)", "name": "specimen_key" },
  { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" },
  { "path": "(effective).ofType(Period).start", "name": "effective_period_start" },
  { "path": "(value).ofType(Quantity).value", "name": "quantity_value" },
  { "path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator" },
  { "path": "(value).ofType(string)", "name": "value_string" }
]
```

The `(effective).ofType(instant)` path was used as a probe-only column (0/5,825
populated); it is deliberately not part of the implementation view because
its native timestamp type can coerce the string choice before the final cast.

The coded group must constrain the coding system inside `forEach`:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

The filtered coding group materialized 5,825 rows for 5,825 distinct
Observations (ratio 1.0), so it did not fan out. Filter the exact string codes
before any integer cast. Do not use `meta.profile` as the discriminator.

Specimen group:

```json
[
  { "path": "getResourceKey()", "name": "specimen_key" },
  { "path": "subject.getReferenceKey(Patient)", "name": "specimen_patient_key" },
  { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", "name": "specimen_id_str" },
  { "path": "collection.collectedDateTime", "name": "collection_datetime" }
]
```

Patient group:

```json
[
  { "path": "getResourceKey()", "name": "patient_key" },
  { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
]
```

Hospital Encounter group:

```json
[
  { "path": "getResourceKey()", "name": "encounter_key" },
  { "path": "subject.getReferenceKey(Patient)", "name": "encounter_patient_key" },
  { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
]
```

The Encounter view must be restricted to
`identifier.system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp'`.
The identifier value is VARCHAR and must become output `CAST(hadm_id_str AS
INTEGER)`. Join Observation to Encounter on `encounter_key` with a LEFT JOIN.

## Source column to FHIR path mapping

| Source column/expression | Canonical FHIRPath column(s) | FHIR/materialized type | Output handling and evidence |
|---|---|---|---|
| `subject_id` (group `MAX`) | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` then `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` | Reference key STRING; identifier value STRING/VARCHAR | Join the UUID key to Patient, cast the identifier value to INTEGER, then `MAX` over the specimen group. Do not use `getResourceKey()` as `subject_id`. |
| `hadm_id` (group `MAX`) | `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` then `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", name: "hadm_id_str"}` | Reference key STRING; identifier value STRING/VARCHAR | LEFT JOIN to hospital Encounters and cast to nullable INTEGER before `MAX`. Missing Observation encounter references must not remove a specimen row. |
| `charttime` per Observation | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | View alias STRING (raw `effectiveDateTime` is string) | Cast to `TIMESTAMP_NTZ` before aggregation if used. `effectiveInstant` is a native raw TIMESTAMP but is not populated for this stream; do not coalesce it with the dateTime string. |
| output `charttime` grouped by specimen | `{path: "collection.collectedDateTime", name: "collection_datetime"}` | STRING/VARCHAR | This is the preferred specimen-level carrier for the output `MAX(charttime)` after the scope check below. Cast only to `TIMESTAMP_NTZ`; the ETL has already applied its TIMESTAMPTZ/DST transform. |
| `specimen_id` grouping key | `{path: "specimen.getReferenceKey(Specimen)", name: "specimen_key"}` then `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value", name: "specimen_id_str"}` | Reference key STRING; identifier value STRING/VARCHAR | Cast `specimen_id_str` to INTEGER. The resource UUID is only a join key; the identifier value is the output natural key. |
| `itemid` | Within the constrained coding group: `{path: "code", name: "item_code"}` and `{path: "system", name: "code_system"}`; optional `{path: "display", name: "item_display"}` | STRING/VARCHAR | The confirmed system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`; filter exact string codes before `CAST(item_code AS INTEGER)`. |
| `valuenum` | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | View alias STRING/VARCHAR; raw `valueQuantity.value` DECIMAL(32,6) | Cast `quantity_value` to DOUBLE and retain only non-null values `> 0`. Do not admit `valueString` or a Quantity merely because it exists. |
| comparator behavior | `{path: "(value).ofType(Quantity).comparator", name: "quantity_comparator"}` | STRING/VARCHAR | 0/5,825 target rows had a comparator. The 32 non-Quantity target values were `valueString`; no comparator-derived Quantity was present for these eleven codes in the authoritative demo. |
| nonnumeric fallback (diagnostic only) | `{path: "(value).ofType(string)", name: "value_string"}` | STRING/VARCHAR | 32/5,825 target rows. They correspond to source rows with `valuenum IS NULL` and are excluded by the source numeric filter. |

The eleven analyte pivots all use the same Quantity path and exact code:

| Source itemid | Output column | Pivot expression (concept SQL) | Output type |
|---:|---|---|---|
| 50861 | `alt` | `MAX(CASE WHEN item_code='50861' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50863 | `alp` | `MAX(CASE WHEN item_code='50863' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50878 | `ast` | `MAX(CASE WHEN item_code='50878' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50867 | `amylase` | `MAX(CASE WHEN item_code='50867' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50885 | `bilirubin_total` | `MAX(CASE WHEN item_code='50885' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50883 | `bilirubin_direct` | `MAX(CASE WHEN item_code='50883' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50884 | `bilirubin_indirect` | `MAX(CASE WHEN item_code='50884' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50910 | `ck_cpk` | `MAX(CASE WHEN item_code='50910' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50911 | `ck_mb` | `MAX(CASE WHEN item_code='50911' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50927 | `ggt` | `MAX(CASE WHEN item_code='50927' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |
| 50954 | `ld_ldh` | `MAX(CASE WHEN item_code='50954' THEN CAST(quantity_value AS DOUBLE) END)` | DOUBLE |

The source uses independent MAX aggregates. Do not select a latest row or
assume that `subject_id`, `hadm_id`, `charttime`, and an analyte came from the
same physical labevent.

## Served-data probes and code confirmation

### Code system, cardinality, and per-code counts

The code system was established by projecting `code.coding` from the served
Observation table, before any cast. For the eleven exact string codes, the
only observed system was
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`.
All eleven codes were present; none was a dead filter. The constrained
`forEach` probe gave 5,825 coding rows / 5,825 distinct resources = 1.0.
Every code display was non-null (the display is not used for filtering).

Counts below are from the authoritative demo. `FHIR coded` is the number of
served coding rows/resources; `FHIR Q` is a non-null Quantity value;
`FHIR cmp` is a non-null Quantity comparator; `FHIR string` is a non-null
valueString; source counts are raw target rows, non-null `valuenum`, and
positive `valuenum` respectively.

| Code | FHIR coded | FHIR Q | FHIR cmp | FHIR string | Source rows | Source valuenum | Source positive |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 50861 | 1,163 | 1,159 | 0 | 4 | 1,163 | 1,159 | 1,159 |
| 50863 | 1,138 | 1,138 | 0 | 0 | 1,138 | 1,138 | 1,138 |
| 50867 | 41 | 41 | 0 | 0 | 41 | 41 | 41 |
| 50878 | 1,165 | 1,165 | 0 | 0 | 1,165 | 1,165 | 1,165 |
| 50883 | 53 | 53 | 0 | 0 | 53 | 53 | 53 |
| 50884 | 47 | 45 | 0 | 2 | 47 | 45 | 44 |
| 50885 | 1,164 | 1,146 | 0 | 18 | 1,164 | 1,146 | 1,146 |
| 50910 | 200 | 200 | 0 | 0 | 200 | 200 | 200 |
| 50911 | 187 | 179 | 0 | 8 | 187 | 179 | 179 |
| 50927 | 4 | 4 | 0 | 0 | 4 | 4 | 4 |
| 50954 | 663 | 663 | 0 | 0 | 663 | 663 | 663 |
| **Total** | **5,825** | **5,793** | **0** | **32** | **5,825** | **5,793** | **5,792** |

The one non-positive numeric source row is itemid 50884 with `valuenum=0`.
The 32 source rows with null `valuenum` are retained in the served stream as
strings for this item set (source text includes `<5.`, `<0.1.`, and similar
values), not as comparator-bearing Quantities. Thus the demo implementation
must select Quantity values and apply the strict `> 0` rule; it must not use
the text fallback to recreate filtered rows.

The source ETL was also checked at
`/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_labevents.sql:15,
27-47,61-77,109-136,163-164`. It writes the itemid verbatim as a string,
writes `effectiveDateTime`, creates an encounter reference only when source
`hadm_id` is non-null, and has a general comparator-text Quantity branch. The
served counts above are the authority for this exact item set.

## Identifier, specimen, time, and encounter checks

### Specimen spine and collection time

The raw served Specimen table had 12,458 resources, with
`specimen_id_str` populated on 11,122/12,458, collection datetime on
12,413/12,458, and a patient reference on 12,458/12,458. Among the 5,792
positive target Observations, the specimen reference, specimen join, and lab
specimen identifier were all 5,792/5,792; those rows covered 1,411 distinct
specimens. The DuckDB source also produced 1,411 retained specimen groups,
and the source/FHIR specimen identifier key sets agreed 1,411/1,411.

`fhir_specimen_lab.sql:4-18,46-59` computes Specimen collection time from
`MAX(charttime)` over all labevents in each specimen, not from the concept's
filtered rows. In the demo, the all-lab MAX and the enzyme-filtered positive
MAX scopes coincided for 1,411/1,411 retained specimens. Comparing the actual
FHIR collection wall time to the DuckDB filtered MAX gave 1,410/1,411 exact:
specimen `48555540` is serialized as `2116-03-08 03:52:00` while the source
filtered MAX is `2116-03-08 02:52:00`. This is the known irreversible
TIMESTAMPTZ/DST-gap normalization, not a different specimen scope. The
upstream specimen SQL casts the MAX through TIMESTAMPTZ at lines 9 and 18;
use `TIMESTAMP_NTZ` to preserve the FHIR wall-clock value and expect this one
intrinsic conflict in the demo.

The source/FHIR aggregate comparison over all 1,411 demo groups found exact
agreement for `subject_id` and all eleven analytes on 1,411/1,411 groups. The
charttime/collection comparison was 1,410/1,411 as stated above.

### Patient and hospital identifiers

The Patient table had 100/100 non-null MIMIC patient identifier values and
100/100 resource keys. Joining the target Observation patient references to
Patient and aggregating the identifier produced the source `MAX(subject_id)`
exactly on 1,411/1,411 retained specimen groups. The served value is a string;
the final output must be INTEGER.

The Encounter table had 637 resources. Its identifier systems were:

| Identifier system | Resources |
|---|---:|
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | 275 |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | 140 |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-ed` | 222 |

Only the first system is valid for `hadm_id`. The hospital identifier value
was populated on 275/637 Encounter resources. Do not use Encounter.class to
select the hospital stream.

For all 5,825 coded target Observations, `patient_key` and `specimen_key` were
5,825/5,825, effective dateTime was 5,825/5,825, and Encounter reference was
4,061/5,825. Restricting to the 5,792 positive Quantity rows, Encounter
reference coverage was 4,036/5,792. The DuckDB target rows likewise had
`hadm_id` on 4,036/5,792 positive rows. At specimen-group level, 1,005/1,411
source groups had a non-null MAX(hadm_id), 406 had null, and the LEFT-joined
FHIR aggregate agreed with the source on `hadm_id` for 1,411/1,411 groups.

This is an item-set-specific coverage coincidence, not evidence that lab
encounter references are complete. Keep the LEFT JOIN. If a full-data row has
no Observation encounter reference while the relational group has a non-null
hadm_id, no exact FHIR path recovers that admission; patient-plus-time is only
a heuristic and must not manufacture an id.

### Effective choice variants and output types

For the exact code/system target, the choice probe returned:

| Path | Materialized type | Non-null / total |
|---|---|---:|
| `(effective).ofType(dateTime)` | STRING | 5,825 / 5,825 |
| `(effective).ofType(instant)` | TIMESTAMP | 0 / 5,825 |
| `(effective).ofType(Period).start` | STRING | 0 / 5,825 |
| `(value).ofType(Quantity).value` | STRING in a ViewDefinition alias; raw field DECIMAL(32,6) | 5,793 / 5,825 |
| `(value).ofType(Quantity).comparator` | STRING | 0 / 5,825 |
| `(value).ofType(string)` | STRING | 32 / 5,825 |

The dateTime, instant, and Period variants must not be COALESCEd together:
the unused native timestamp variant would cause Spark timezone coercion. Cast
the dateTime/collection strings directly to `TIMESTAMP_NTZ`, and keep the
outer output type `TIMESTAMP_NTZ` rather than a late plain TIMESTAMP cast.
The numeric aliases require `CAST(quantity_value AS DOUBLE)` before MAX and
before the final DOUBLE output.

## Gaps and representability

1. **`charttime`: not representable for a DST-gap wall time.** The specimen
   collection element is present and has the correct all-lab/filtered MAX
   scope for 1,411/1,411 demo groups, but the ETL's TIMESTAMPTZ cast changed
   one source `02:52` value to FHIR `03:52`. No query over FHIR can recover the
   original wall time. The measured demo agreement is 1,410/1,411.
2. **`hadm_id`: potentially not representable when the Observation encounter
   reference is absent.** A hospital Encounter identifier is the exact path
   when the reference exists. Patient/time admission-window matching is only
   an approximation and was not used. For this item set on the demo, missing
   references coincided with source-null group MAX values, so the measured
   aggregate agreement was 1,411/1,411; this does not remove the general
   FHIR coverage gap.
3. **No gap found for `specimen_id`, `subject_id`, or the eleven positive
   analytes in the demo.** Their exact keyed aggregate agreement was
   1,411/1,411 for each field. The 32 source rows with null `valuenum` are
   intentionally filtered out, not missing selected output rows.

## Notes and fragments used

Curated `MIMIC_NOTES.md` entries that changed this mapping decision were:

- MIMIC ids live in `identifier.value` as strings: use Patient/Encounter /
  Specimen identifier values and cast only in the outer SQL, never use UUID
  resource/reference keys as output ids.
- Observation item codes are verbatim source itemids and must be filtered by
  system plus exact string code, never by `meta.profile` and never before the
  system guard with an integer cast.
- Lab Observation specimen references preserve `labevents.specimen_id` and
  are the grouping spine.
- Lab Observation encounter references are incomplete: retain rows with a
  LEFT JOIN and measure the item-set-specific hadm coverage.
- Quantity ViewDefinition aliases are string-like and need a numeric cast.
- FHIR datetimes carry offsets but are de-identified wall-clock values: use
  `TIMESTAMP_NTZ`, and account for the known DST-gap transform.

I read `MIMIC_NOTES.d/README.md` and the relevant provisional fragments
`chemistry.md`, `coagulation.md`, `complete_blood_count.md`,
`blood_differential.md`, and `cardiac_marker.md` (and confirmed there was no
pre-existing `enzyme.md` fragment). Their relevant leads about lab specimen
display, comparator-text quantities, datetime choice coercion, and filtering
codes before casts were checked against the served Delta and upstream ETL;
the fragments themselves were treated as provisional, not as evidence. No
new dataset-wide quirk not already covered by curated `MIMIC_NOTES.md` was
found, so `MIMIC_NOTES.d/enzyme.md` was not appended.

No attempt ViewDefinition or concept SQL was authored by this stage.
