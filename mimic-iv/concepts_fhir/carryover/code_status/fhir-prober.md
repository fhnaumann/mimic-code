# FHIR probe and mapping: `code_status`

**Concept:** `treatment/code_status`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/code_status/source-analyst.md`  
**Probed:** 2026-08-10  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2; no HTTP Pathling server  
**DuckDB oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, read-only

## Result and comparison shape

The ICU `chartevents` branch is representable through FHIR `Observation`.
The hospital POE code-status branch is not present in the served FHIR
resources: no exact FHIR resource preserves its POE event, selector values,
or `poe_detail.field_value`. A port can reproduce the chart branch exactly,
but must declare the POE branch as a coverage gap rather than mapping it to
the unrelated medication POE requests.

The immutable full oracle declares eight columns, all `INTEGER` except
`charttime` (`TIMESTAMP`), `comparison: full_tuple_multiset`, `key: null`,
and `row_count: 269072`. Do not use a FHIR UUID, `poe_id`, or
`(subject_id, hadm_id, stay_id, charttime)` as a natural key. The source
projection omits event identity, `UNION ALL` preserves duplicates, and both
the detail join and ICU interval join can multiply rows on full data.

The demo source has 147 chart rows plus 242 POE/detail rows = 389 union rows.
The targeted chart FHIR projection has 147 rows and 147 distinct resource
keys. The demo is not evidence that the final four-column tuple is a full-data
key.

## Resource mappings and discriminators

| Source stream | FHIR resource/path | Discriminator and observed result |
|---|---|---|
| `mimiciv_icu.chartevents` where `itemid = 223758` | `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and exact `code = '223758'`; display is `Code Status` |
| `mimiciv_hosp.poe` + `poe_detail` where `order_type = 'General Care'` and `order_subtype = 'Code status'` | **No exact served FHIR resource** | The served `MedicationRequest` POE identifier stream is a different medication/IV subset; its 2,327 IDs had zero intersection with the 242 code-status POE IDs. |
| `mimiciv_icu.icustays` used by the POE interval join | `Encounter` with ICU identifier and `period` | For represented chart observations, follow `Observation.encounter` to an ICU Encounter; use its ICU identifier for `stay_id`, `partOf` for the hospital Encounter, and the hospital identifier for `hadm_id`. |

Use `system + exact code`, never `meta.profile`, as the chart
discriminator. The authoritative Delta has the chart subtype profile on all
147 target rows, but the shared notes record that subtype profiles vary by
warehouse preparation. The base code-system binding is portable. The full
Observation coding cross-tab from an unfiltered `forEach: "code.coding"` was:

```text
http://loinc.org                                                        9042
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items    668862
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items                 24642
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems             107727
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-antibiotic 1036
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-organism  338
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-microbiology-test      1893
```

Every row in that cross-tab had exactly one coding (`count(coding rows) /
count(distinct resource key) = 1.0`). For the target code specifically,
the only system was the chartevents system above: 147 coding rows / 147
Observation resources = **1.0**. Keep the system/code predicate inside the
coding `forEach` even though the present ratio is one.

## Canonical ViewDefinition extraction mappings

These are mapping fragments only; no ViewDefinition or concept SQL was
authored. All UUID/resource/reference keys below are join-only strings, not
the final MIMIC integer identifiers.

### Target chart Observation

The coding group should be constrained inside `forEach`:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items').where(code='223758')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "item_display" }
  ]
}
```

| Source column/role | Canonical `{path, name}` | FHIR type | Materialized/use type |
|---|---|---|---|
| chart event identity (join support only) | `{ "path": "getResourceKey()", "name": "observation_key" }` | resource key string | `VARCHAR`; never output/key the concept |
| `subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`, then Patient `subject_id_str` below | `Reference(Patient)` | `VARCHAR` join key; final identifier cast to `INTEGER` |
| `hadm_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }`, then ICU `partOf` → hospital Encounter `hadm_id_str` below | `Reference(Encounter)` | `VARCHAR` join keys; final identifier cast to `INTEGER` |
| `stay_id` | ICU Encounter identifier below, reached from `icu_encounter_key` | `Identifier.value` string | `VARCHAR`; final cast to `INTEGER` |
| `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `dateTime` | Pathling materializes a string with offset; final `CAST(... AS TIMESTAMP_NTZ)` |
| unused effective choice check | `{ "path": "(effective).ofType(Period).start", "name": "effective_period_start" }` | `Period.start` `dateTime` | `VARCHAR`; 0/147 populated in the target |
| source `value` | `{ "path": "(value).ofType(string)", "name": "value_string" }` | `string` | `VARCHAR`; final flags are `INTEGER` CASE expressions |

Target `value` is not a CodeableConcept and has no numeric Quantity value:
`value_string` was 147/147 non-null and `quantity_value` was 0/147. The
exact status comparisons are:

```text
fullcode = 1 when value_string = 'Full code'
cmo      = 1 when value_string = 'Comfort measures only'
dni      = 1 when value_string IN ('DNI (do not intubate)', 'DNR / DNI')
dnr      = 1 when value_string IN ('DNR (do not resuscitate)', 'DNR / DNI')
```

The FHIR coding `code`, `system`, and `display` paths above were all 147/147
non-null; `effective_datetime`, patient reference, and ICU Encounter
reference were also 147/147 non-null.

### Patient identifier spine

```json
{
  "resource": "Patient",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "patient_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
    ]
  }]
}
```

`subject_id_str` is FHIR `Identifier.value` (`string`/materialized `VARCHAR`),
not `getResourceKey()`. The demo Patient view had 100/100 resource keys and
100/100 patient identifiers. Cast only at the final output boundary.

### ICU Encounter and hospital Encounter spine

```json
{
  "resource": "Encounter",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "icu_encounter_key" },
      { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" },
      { "path": "partOf.getReferenceKey(Encounter)", "name": "hosp_encounter_key" },
      { "path": "period.start", "name": "intime_str" },
      { "path": "period.end", "name": "outtime_str" }
    ]
  }]
}
```

```json
{
  "resource": "Encounter",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "hosp_encounter_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
    ]
  }]
}
```

`identifier.where(...)` avoids an unnecessary identifier fan-out. The ICU
view has 637 Encounter rows, of which 140 carry an ICU identifier; the
hospital view has 275 hospital identifiers among 637 Encounter rows. On the
147 target chart rows, the chain

```text
Observation.encounter.getReferenceKey(Encounter)
  -> Encounter.identifier(...encounter-icu).value       = stay_id
  -> Encounter.partOf.getReferenceKey(Encounter)
  -> parent Encounter.identifier(...encounter-hosp).value = hadm_id
```

resolved the ICU Encounter, `stay_id`, parent hospital Encounter, `hadm_id`,
and Patient identifier **147/147**. Use `LEFT JOIN`s in a candidate so a
future missing reference remains a typed NULL rather than dropping a source
row; the present target mapping is complete.

### POE/ICU negative-control and gap probe

The only served POE identifier stream found was on `MedicationRequest`:

```json
{
  "resource": "MedicationRequest",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "medreq_key" },
      { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
      { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
      { "path": "authoredOn", "name": "authored_on_str" },
      { "path": "status", "name": "status" }
    ]
  }, {
    "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-poe')",
    "column": [
      { "path": "system", "name": "identifier_system" },
      { "path": "value", "name": "poe_id" }
    ]
  }]
}
```

This negative-control view yielded 2,327/2,327 identifier values,
`authoredOn`, and `status`, all with the medication-request-poe system. The
242 source code-status `poe_id`s had **zero** intersection with those 2,327
FHIR IDs. Therefore do not use `MedicationRequest.authoredOn` as the source
`p.ordertime`, `MedicationRequest.status` as a code-status flag, or its
medication coding as `pd.field_value`.

## Source filters, exact literals, and row counts

### ICU chart stream

The exact source filter is `mimiciv_icu.chartevents.itemid IN (223758)`. In
DuckDB this returned 147 rows: `subject_id`, `hadm_id`, `stay_id`, `charttime`,

```text
'Comfort measures only'    1
'DNI (do not intubate)'    1
'DNR (do not resuscitate)' 3
'DNR / DNI'                3
'Full code'              139
```

The served coding projection returned exactly the same code and display:
`223758` / `Code Status` / the chartevents-d-items system, 147 rows. The
served `value.ofType(string)` counts were exactly the five counts above.
The chart flag totals were `fullcode=139`, `cmo=1`, `dni=4`, and `dnr=6`.

### POE stream

The exact selector is:

```sql
WHERE p.order_type = 'General Care'
  AND p.order_subtype = 'Code status'
```

The inner join is exactly `p.poe_id = pd.poe_id`; in the demo it returned
242 rows, 242 distinct POE IDs, and every `p.subject_id`, `p.hadm_id`,
`p.ordertime`, `p.poe_id`, and `pd.field_value` was non-null. The exact
`pd.field_value` literals and counts were:

```text
'DNAR (DO NOT attempt resuscitation for cardiac arrest) '  19
'Do not resuscitate (DNR/DNI)'                            42
'Full code  (attempt resuscitation)'                      37
'Resuscitate (Full code)'                                144
```

The first literal has one trailing ASCII space before the closing quote; the
second full-code literal has two spaces between `code` and `(`. POE flag
totals are `fullcode=181`, `cmo=0` (the SQL supplies a constant zero),
`dni=42`, and `dnr=61`.

The source POE-to-ICU join is a `LEFT JOIN` on `p.hadm_id = ie.hadm_id` with
inclusive bounds `p.ordertime >= ie.intime` and `p.ordertime <= ie.outtime`.
The demo produced 92 matched `stay_id` rows and 150 NULL `stay_id` rows;
there were 57 distinct matched stays and no observed interval fan-out. This
join cannot be performed for the missing code-status POE event in FHIR. The
FHIR ICU equivalents of `ie.intime`/`ie.outtime` are
`Encounter.period.start`/`.end`, but they do not restore the absent POE row.

## Oracle agreement and multiplicity

The exact probe used `EmbeddedExecutor` with inline ViewDefinitions over the
Delta warehouse, then ran:

```sql
SELECT CAST(p.subject_id_str AS INT) AS subject_id,
       CAST(h.hadm_id_str AS INT) AS hadm_id,
       CAST(i.stay_id_str AS INT) AS stay_id,
       CAST(c.effective_datetime AS TIMESTAMP_NTZ) AS charttime,
       c.value_string
FROM cs_chart c
LEFT JOIN cs_icu i ON c.icu_encounter_key = i.icu_encounter_key
LEFT JOIN cs_hosp h ON i.hosp_encounter_key = h.hosp_encounter_key
LEFT JOIN cs_patient p ON c.patient_key = p.patient_key
```

The eight-column chart projection (including the four CASE flags) was
compared in Python as a `collections.Counter` against the DuckDB query:

```sql
SELECT subject_id, hadm_id, stay_id, charttime,
       CASE WHEN "value" IN ('Full code') THEN 1 ELSE 0 END AS fullcode,
       CASE WHEN "value" IN ('Comfort measures only') THEN 1 ELSE 0 END AS cmo,
       CASE WHEN "value" IN ('DNI (do not intubate)','DNR / DNI') THEN 1 ELSE 0 END AS dni,
       CASE WHEN "value" IN ('DNR (do not resuscitate)','DNR / DNI') THEN 1 ELSE 0 END AS dnr
FROM mimiciv_icu.chartevents
WHERE itemid = 223758
```

Result: **147 FHIR rows, 147 DuckDB rows, exact multiset agreement True**;
the chart resource key was distinct for all 147 rows. The FHIR mapping
therefore recovers every chart output field exactly in the demo, including
the ICU stay linkage and wall-clock timestamp after `TIMESTAMP_NTZ` casting.

## Gaps

* **POE event branch — not representable.** The served Delta has no exact
  resource for the 242 selected code-status POEs. `poe_id`, the association
  of `subject_id`/`hadm_id` with that POE event, `ordertime`,
  `order_type`, `order_subtype`, and `poe_detail.field_value` cannot be
  reconstructed from the available FHIR resources. The corresponding
  oracle rows are an intrinsic FHIR coverage gap, not a reason to invent a
  MedicationRequest mapping.
* **POE ICU `stay_id` — absent because the POE row is absent.** ICU
  `Encounter.identifier(...encounter-icu).value` and its period are present
  and exact for chart observations, but no FHIR event carries the POE
  `ordertime` needed to apply the source interval join. Patient/time or
  hospital-Encounter heuristics would manufacture associations and are not
  an exact derivation.
* **No gap for the chart branch.** Patient and Encounter identifier values,
  the chart code, value string, dateTime, ICU stay, and hospital admission
  were all populated for the 147 target rows and agreed 147/147 with DuckDB.
* **No natural key.** This is a comparison-shape constraint, not a missing
  FHIR field: retain full tuple multiplicity and compare as the manifest's
  `full_tuple_multiset`.

## Shared notes and fragment handling

The following established entries changed mapping decisions:

* `MIMIC ids live in identifier.value as STRINGs` made Patient and Encounter
  identifiers the source IDs and kept UUID resource/reference keys join-only.
* `Observation.code.coding.code is the source itemid, verbatim` established
  exact code `223758` and ruled out terminology translation.
* `Observation subtype profile metadata is warehouse-version dependent` ruled
  out `meta.profile` as the stream discriminator.
* `Categorical chartevents store their label in valueString` selected
  `(value).ofType(string)` for all chart statuses.
* `Encounter has three identifier systems — class discriminates none` and
  the ICU `partOf`/identifier spine established the `stay_id` and `hadm_id`
  chain.
* `FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ` governs
  `effective_datetime` and Encounter period values.

Read all existing provisional fragments in `MIMIC_NOTES.d/`:
`README.md`, `coagulation.md`, `cardiac_marker.md`, `blood_differential.md`,
and `chemistry.md`. Their labevents-specific claims were not adopted as
code-status evidence; the relevant general string-code and datetime handling
was independently checked by the probes above. `MIMIC_NOTES.md` was not
edited. A genuinely dataset-wide ETL finding was appended to the owned
fragment `MIMIC_NOTES.d/code_status.md`: the chartevents ETL excludes one
hard-coded `(stay_id, charttime)` duplicate before writing any chart
Observation; the demo query found zero rows at that key, so it did not affect
this concept's 147-row target probe. A second appended entry records the
dataset-wide `value IS NOT NULL` ETL filter; the target had zero NULL values,
so it also did not affect this concept's demo probe.

## Probe command record

The warehouse probes were run with these command forms from the repository
root:

```bash
uv run python - <<'PY'   # EmbeddedExecutor + Pathling ViewDefinitions above
# EmbeddedExecutor('/Users/nau025/warehouses/mimic-iv-demo/delta', ...)
# materialise cs_chart, cs_icu, cs_hosp, cs_patient, cs_medreq and run the
# count/system/code/value/join SQL recorded in this file.
PY

uv run python - <<'PY'   # DuckDB source and Counter oracle check
# duckdb.connect('/Users/nau025/warehouses/mimic4-demo.db', read_only=True)
# run the exact chartevents/POE SQL and compare the chart Counter.
PY
```

No ViewDefinition artifact, concept SQL, or immutable attempt artifact was
written. This carryover file and the owned notes fragment are the reusable
mapping artifacts.
