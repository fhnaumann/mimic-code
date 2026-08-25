# FHIR prober mapping — `gcs` (attempt_0007, rebuilt warehouse)

**Concept:** `measurement/gcs`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/gcs/source-analyst.md`  
**Canonical source SQL:** `mimic-iv/concepts/measurement/gcs.sql`  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Probe engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Source oracle:** `/Users/nau025/warehouses/mimic-iv-duckdb-demo/icu/*.csv.gz`, DuckDB  
**No stale NDJSON or HTTP Pathling server was used.**

## Reopened-attempt instruction applied

> Upstream e7c326b (#125) now carries chartevents.value in
> Observation.component[].valueString, coded with the same mimic-chartevents-
> d-items coding as Observation.code. itemid 223900 therefore distinguishes
> 'No Response' from 'No Response-ETT' again. The unrepresentability-
> declaration for gcs_unable is now FALSE and must be removed: select the
> component text and derive gcs_unable from it, and drop the ambiguity-
> propagation logic that emitted NULL for gcs, gcs_motor, gcs_verbal and
> gcs_eyes on affected windows. Do not reconstruct any resource id.

The rebuilt Delta probe confirms this instruction. The component text is
populated alongside `valueQuantity` for all 9,791 selected GCS Observations;
`223900` has 1,348 `No Response-ETT` and 78 `No Response` component values.
`gcs_unable` is therefore representable from the component text, and the old
whole-concept label-loss declaration and quantity-1 heuristic are superseded.
Resource/reference keys were used only for equality joins and were not parsed,
regenerated, hashed, enumerated, hardcoded, or used to infer a source value.

## Resource and stream mapping

| MIMIC-IV source | MIMIC-on-FHIR resource/interface | Role |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation` with `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` | Three item-coded GCS streams; pivot source for the concept |
| `chartevents.subject_id` | `Observation.subject` → `Patient` | Equality join through the Patient resource key; numeric id comes from Patient.identifier |
| `chartevents.stay_id` | `Observation.encounter` → ICU `Encounter` | Equality join through the ICU Encounter resource key; numeric id comes from the ICU identifier |
| `Patient.identifier` | Patient identifier system `http://mimic.mit.edu/fhir/mimic/identifier/patient` | `subject_id` string before the final integer cast |
| ICU `Encounter.identifier` | Encounter identifier system `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | `stay_id` string before the final integer cast and ICU stream discriminator |

The Delta contains 813,540 `Observation` resources. The constrained
chartevents coding projection contains 668,862 coding rows over 668,862
distinct resources (ratio 1.000). The GCS projection contains 9,791 rows over
9,791 distinct resources (ratio 1.000).

## Coded discriminator and exact code set

The discriminator is the exact pair `code.coding.system` + `code.coding.code`,
never `meta.profile`:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
codes  = "223900", "223901", "220739"
```

Use the coding restriction inside the `forEach`:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code='223900' or code='223901' or code='220739'))",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "item_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

| Source itemid | FHIR code/display | coding rows | distinct resources | ratio |
|---:|---|---:|---:|---:|
| 220739 | `"220739"` / `GCS - Eye Opening` | 3,274 | 3,274 | 1.000 |
| 223900 | `"223900"` / `GCS - Verbal Response` | 3,266 | 3,266 | 1.000 |
| 223901 | `"223901"` / `GCS - Motor Response` | 3,251 | 3,251 | 1.000 |
| **target total** | — | **9,791** | **9,791** | **1.000** |

No other system was present for the target rows. A served `CodeSystem` resource
is not present in the Delta (`read("CodeSystem")` raises `No data found for
resource type: CodeSystem`), so the system/code confirmation is from the
served Observation codings, the current ETL, and the source `d_items` rows.
The GCS chartevents system is distinct from the shared `mimic-d-items` system
used by outputevents/datetimeevents. In general, where those two streams share
that system, the exact code remains sufficient because `d_items.itemid` is a
global primary key with one `linksto` value per item; this GCS filter does not
depend on that shared-system case.

## Canonical source-column → FHIRPath mapping

ViewDefinition aliases for `Identifier.value`, keys, `dateTime`, Quantity
values, and component text are materialized as Spark strings unless stated
otherwise. The implementer must cast the identifier aliases to `INTEGER`, the
effective alias to `TIMESTAMP_NTZ`, and the Quantity alias to `DOUBLE`/the
manifest's `FLOAT` output type in the derived SQL. Resource keys remain opaque
strings with their `Type/uuid` prefix.

### Observation extraction

| Source column / role | Canonical `{path, name}` | FHIR type | Probe rows / non-null and required target type |
|---|---|---|---|
| `chartevents.subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `Reference(Patient)` key string | 9,791 / 9,791; equality join only; emit `patient_key` unchanged |
| `chartevents.stay_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` | `Reference(Encounter)` key string | 9,791 / 9,791; equality join only; emit `icu_encounter_key` unchanged |
| `chartevents.charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `Observation.effectiveDateTime`; Pathling alias `STRING` | 9,791 / 9,791; `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` → `charttime TIMESTAMP` |
| `chartevents.itemid` | `{ "path": "code", "name": "item_code" }` inside the constrained `code.coding` group | `Coding.code` string | 9,791 / 9,791; exact decimal strings; cast to integer only after system/code filtering |
| coding system | `{ "path": "system", "name": "item_system" }` inside the constrained `code.coding` group | `Coding.system` string | 9,791 / 9,791; exact proprietary URI |
| `d_items.label` | `{ "path": "display", "name": "item_display" }` inside the constrained `code.coding` group | `Coding.display` string | 9,791 / 9,791; display agrees with `d_items.label` 9,791 / 9,791; not a discriminator |
| `chartevents.valuenum` | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` decimal; Pathling alias `STRING` | 9,791 / 9,791; cast to `DOUBLE`/manifest `FLOAT` |
| `chartevents.valueuom` (not used by canonical SQL) | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | `Quantity.unit` string | 0 / 9,791; source `valueuom` is NULL on 9,791 / 9,791; do not use for GCS |
| `chartevents.value` for the `223900` verbal sentinel | `{ "path": "component.where(code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and code.coding.code='223900').value.ofType(string)", "name": "component_text_223900" }` | `Observation.component[].valueString` string | 3,266 / 3,266 on item `223900`; all component texts populated; use exact text to derive `gcs_unable` and verbal sentinel 0 |
| component coding for the selected component | `{ "path": "code.coding.code", "name": "component_code" }`, `{ "path": "code.coding.system", "name": "component_system" }`, `{ "path": "code.coding.display", "name": "component_display" }` inside `forEachOrNull` over the selected component | `Coding.code/system/display` strings | 9,791 / 9,791; component code/system/display equal Observation code/system/display on 9,791 / 9,791 |
| component text for all selected GCS items | `{ "path": "value.ofType(string)", "name": "component_text" }` inside `forEachOrNull: "component.where(code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code.coding.code='223900' or code.coding.code='223901' or code.coding.code='220739'))"` | `Observation.component[].valueString` string | 9,791 / 9,791; this is the generic projection; current GCS rows have one matching component each |
| top-level source text alternative | `{ "path": "(value).ofType(string)", "name": "value_string" }` | top-level `Observation.valueString` string | 0 / 9,791 because all selected rows also have Quantity; do not use it for GCS |
| resource identity (support only) | `{ "path": "getResourceKey()", "name": "observation_key" }` | opaque `Observation` resource key string | 9,791 / 9,791 and distinct; never output as a source id and never decode or regenerate it |

The canonical component group is:

```json
{
  "forEachOrNull": "component.where(code.coding.system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items' and (code.coding.code='223900' or code.coding.code='223901' or code.coding.code='220739'))",
  "column": [
    { "path": "code.coding.code", "name": "component_code" },
    { "path": "code.coding.system", "name": "component_system" },
    { "path": "code.coding.display", "name": "component_display" },
    { "path": "value.ofType(string)", "name": "component_text" }
  ]
}
```

The direct encoded branch is `component[].valueString`; the `.value.ofType(string)`
FHIRPath above is the canonical choice-type projection. The current Delta probe
also returned the same values from the direct `valueString` path on 9,791 / 9,791
rows.

### Patient and ICU Encounter support views

```json
{
  "resource": "Patient",
  "select": [{"column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]}]
}
```

```json
{
  "resource": "Encounter",
  "select": [{"column": [
    { "path": "getResourceKey()", "name": "icu_encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
    { "path": "period.start", "name": "intime_datetime" }
  ]}]
}
```

The unfiltered Encounter view has 637 rows, but `stay_id_str` is populated on
only 140 ICU Encounters; filter the ICU stream with the ICU identifier system,
never with `Encounter.class`. The Patient view has 100 rows and 100 populated
patient keys/identifier values. All 9,791 target Observation rows had a
resolvable Patient and ICU Encounter equality join, and both identifier values
were non-null on all joined rows.

The final derived output must cast `subject_id_str` and `stay_id_str` to
`INTEGER` and emit the required opaque companions `patient_key` and
`icu_encounter_key`. Neither integer is obtained from a resource id.

## Derived GCS fields after the component fix

`gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, and `gcs_unable` are derived
columns, not direct FHIR elements. Use the source analysis's exact grouping at
`(stay_id, charttime)`, `MAX` pivots by exact item code, immediate previous-row
six-hour carry-forward, and defaults `(6, 5, 4)`.

* `gcs_motor` comes from Quantity value for code `223901`.
* `gcs_eyes` comes from Quantity value for code `220739`.
* `gcs_verbal` comes from Quantity value for code `223900`, except the exact
  component text `No Response-ETT`, which maps to numeric sentinel `0`.
* `gcs_unable` is `1` exactly when the current `223900` component text is
  `No Response-ETT`, otherwise `0` under the source CASE expression.
* The ETT branch yields total `gcs = 15`; the existing source-analysis
  ambiguity-propagation NULL logic must not be retained now that the component
  text is served.

The source label is now directly available, not approximated by Quantity 1:
1,348 `No Response-ETT` and 78 `No Response` rows both have Quantity 1, but
their component texts are distinct. The prior 94.53% quantity-1 heuristic is
obsolete and must not be used.

## Probe counts, NULLs, duplicates, and source agreement

### Rebuilt Delta path counts

For the 9,791 target rows (rows / non-null):

| Projection | Rows | Non-null |
|---|---:|---:|
| `getResourceKey()` / `observation_key` | 9,791 | 9,791 |
| `subject.getReferenceKey(Patient)` / `patient_key` | 9,791 | 9,791 |
| `encounter.getReferenceKey(Encounter)` / `icu_encounter_key` | 9,791 | 9,791 |
| `(effective).ofType(dateTime)` | 9,791 | 9,791 |
| `(effective).ofType(Period).start` | 9,791 | 0 |
| `(effective).ofType(Period).end` | 9,791 | 0 |
| `(effective).ofType(instant)` | 9,791 | 0 |
| `(value).ofType(Quantity).value` | 9,791 | 9,791 |
| `(value).ofType(Quantity).unit` | 9,791 | 0 |
| `(value).ofType(string)` | 9,791 | 0 |
| selected component code/system/display/text | 9,791 each | 9,791 each |

Per-code Delta counts are 3,274 / 3,274 / 3,251 for `220739` / `223900` /
`223901`, respectively. The component code, system, and display match the
Observation coding on 9,791 / 9,791 rows. Component text distributions include
`223900`: `No Response-ETT` 1,348 and `No Response` 78.

### Source-side NULL and duplicate checks

The read-only DuckDB source query over `chartevents.csv.gz` returned:

| itemid | total | `value` non-null | `value` NULL | `valuenum` non-null | `valueuom` non-null |
|---:|---:|---:|---:|---:|---:|
| 220739 | 3,274 | 3,274 | 0 | 3,274 | 0 |
| 223900 | 3,266 | 3,266 | 0 | 3,266 | 0 |
| 223901 | 3,251 | 3,251 | 0 | 3,251 | 0 |

The selected source has 9,791 grouped `(stay_id, charttime, itemid)` keys,
zero duplicate keys, and maximum multiplicity one. The ETL hard-coded tuple
`(stay_id=34934165, charttime='2151-10-03 05:14:00')` has zero selected source
rows in this probe. Thus the global ETL `value IS NOT NULL` and hard-coded
tuple omissions have a zero-row bound for the demo GCS target, although the
canonical SQL has no such predicates and the full run must still measure any
full-data coverage loss. The broader chartevents stream can retain repeated
same-item rows; this GCS-specific probe found none.

### Oracle agreement

After equality joining the FHIR Observation references to Patient and ICU
Encounter views, the source/FHIR join on
`(subject_id, stay_id, charttime, itemid)` was exact:

* source rows 9,791; candidate rows 9,791; paired keys 9,791;
  source-only 0; candidate-only 0;
* identifiers `subject_id`/`stay_id`: 9,791 / 9,791 exact;
* effective `charttime`: 9,791 / 9,791 exact using `TIMESTAMP_NTZ`;
* Quantity numeric value: 9,791 / 9,791 exact;
* component text versus source `value`: 9,791 / 9,791 exact;
* component code and system: 9,791 / 9,791 exact;
* `d_items.label` versus FHIR display: 9,791 / 9,791 exact.

## Gaps and representability status

* **The former GCS label gap is resolved.** `chartevents.value` for the
  numeric GCS rows is represented by `Observation.component[].valueString`,
  with the exact item coding. `gcs_unable` is not unrepresentable; remove any
  declaration and derive it from the component text. Do not emit ambiguity
  NULLs for `gcs`, `gcs_motor`, `gcs_verbal`, or `gcs_eyes` on ETT windows.
* **Potential ETL row-coverage gap:** the upstream chartevents ETL excludes
  source rows with `value IS NULL` and one hard-coded tuple, whereas the
  canonical GCS filter names only itemids. Such an omitted row is absent and
  not representable from FHIR. The measured GCS demo bound is 0 rows, and no
  whole-concept recommendation follows from this probe; the full comparison
  must bound whether any omitted rows affect grouping, carry-forward, or row
  selection.
* **Quantity unit:** absent on 9,791 / 9,791 rows, but source `valueuom` is
  also NULL on all selected rows and the canonical SQL never consumes it. This
  is an ancillary absent field, not a GCS derivation gap.
* **Resource identity:** `Observation.getResourceKey()` is opaque identity
  only. It is not a source-column mapping and cannot recover text or time.
* **Effective choice variants:** Period and instant are absent for this
  stream; the dateTime projection is complete at 9,791 / 9,791, so no
  effective-time COALESCE is needed. Parse the offset-bearing alias as a MIMIC
  wall clock with `TIMESTAMP_NTZ`, not an offset-aware conversion.

## Notes and provisional leads consulted

Read the canonical source analysis, the full `MIMIC_NOTES.md`, the canonical
`v_observation.viewdefinition.json`, the current
`mimic-fhir/sql/fhir_observation_chartevents.sql`, and the MIMIC_NOTES.d
protocol. Relevant provisional fragments read were `gcs.md`, `first_day_gcs.md`,
`first_day_vitalsign.md`, `crrt.md`, `code_status.md`, `cardiac_marker.md`,
`oxygen_delivery.md`, `icp.md`, `height.md`, `vitalsign.md`,
`ventilator_setting.md`, `icustay_detail.md`, `chemistry.md`, and
`coagulation.md`. Fragment claims were treated as leads and checked against
the rebuilt Delta/source probe; historical UUID-recovery recommendations were
not adopted because resource ids are opaque.

Curated `MIMIC_NOTES.md` entries that changed this mapping decision:

* Delta tables, not NDJSON or the unauthorized HTTP server, are authoritative.
* Upstream `e7c326b` now preserves numeric chartevents text in a component;
  this supersedes the historical GCS label-loss/block entry.
* Item codes are verbatim source itemids; discriminate with exact system +
  code, never `meta.profile`.
* Identifier values are strings and must be cast, while resource/reference
  keys are separate opaque equality keys and required companions.
* FHIR dateTime aliases require `TIMESTAMP_NTZ` wall-clock parsing and choice
  variants should be projected with `ofType()`.
* Chartevents has global NULL-value/hard-coded-tuple omissions and can retain
  repeated rows; this probe measured zero affected GCS rows and zero GCS
  same-item duplicates in the demo.

`MIMIC_NOTES.d/gcs.md` was read as provisional. Its old numeric-text-loss and
whole-concept unrepresentability claims are superseded by the rebuilt component
probe; its opaque-id warnings remain obeyed. No new dataset-wide quirk absent
from curated `MIMIC_NOTES.md` and the owned `gcs.md` fragment was found, so no
fragment section was appended.

## Artifacts

Updated mutable carryover mapping:

`mimic-iv/concepts_fhir/carryover/gcs/fhir-prober.md`

No ViewDefinition, `concept.sql`, or immutable attempt artifact was authored by
this stage. The orchestrator should store this evidence at
`mimic-iv/concepts_fhir/concepts/measurement/gcs/attempt_0007/evidence/fhir-prober.md`.
