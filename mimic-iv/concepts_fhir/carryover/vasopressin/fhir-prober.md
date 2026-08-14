# FHIR prober mapping: `vasopressin`

## Scope and authoritative probes

- Source: `mimic-iv/concepts/medication/vasopressin.sql`.
- Sole source table: `mimiciv_icu.inputevents`; no source joins, aggregates,
  windows, or dependencies.
- FHIR resource: `MedicationAdministration`, the ICU inputevent stream.
- Warehouse probed: `/Users/nau025/warehouses/mimic-iv-demo/delta`, using
  embedded Pathling 9.6.0 on Spark. The local DuckDB source oracle used for
  the cheap check was `/Users/nau025/warehouses/mimic4-demo.db`.
- The demo target had 55 source rows and 55 target MedicationAdministration
  rows. The full oracle manifest records 25,892 rows and comparison key
  `(stay_id, starttime)`; that full count is manifest metadata, not a local
  full-data probe.

## Canonical ViewDefinition select.column blocks

The following are the exact column groups to use. ViewDefinition aliases for
FHIR strings, references, choice values, and Quantity values are materialized
as `VARCHAR`/string-like columns and must be cast in the final SQL when the
manifest requires another type.

### `MedicationAdministration` view

Flat group:

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "medadmin_key"},
    {"path": "context.getReferenceKey(Encounter)", "name": "encounter_key"},
    {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
    {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
    {"path": "(effective).ofType(Period).start", "name": "effective_period_start"},
    {"path": "(effective).ofType(Period).end", "name": "effective_period_end"},
    {"path": "(dosage.rate).ofType(Quantity).value", "name": "rate_value"},
    {"path": "(dosage.rate).ofType(Quantity).unit", "name": "rate_unit"},
    {"path": "(dosage.rate).ofType(Quantity).system", "name": "rate_system"},
    {"path": "(dosage.rate).ofType(Quantity).code", "name": "rate_code"},
    {"path": "(dosage.dose).ofType(Quantity).value", "name": "amount_value"},
    {"path": "(dosage.dose).ofType(Quantity).unit", "name": "amount_unit"},
    {"path": "(dosage.dose).ofType(Quantity).system", "name": "amount_system"},
    {"path": "(dosage.dose).ofType(Quantity).code", "name": "amount_code"}
  ]
}
```

Coding group, constrained inside `forEach`:

```json
{
  "forEach": "medication.ofType(CodeableConcept).coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu' and code='222315')",
  "column": [
    {"path": "code", "name": "item_code"},
    {"path": "system", "name": "code_system"},
    {"path": "display", "name": "code_display"}
  ]
}
```

The `forEach` is safe here: the authoritative Delta has exactly one coding
per MedicationAdministration (56,535 coding rows / 56,535 distinct resources
= 1.000 overall; 20,404/20,404 in the ICU system; 55/55 for vasopressin).

### ICU `Encounter` view

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "encounter_key"},
    {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"}
  ]
}
```

`stay_id_str` is a FHIR `identifier.value`, therefore `VARCHAR`, not the
opaque `Encounter` resource key. The encounter view contains 637 resources;
the ICU identifier is non-null on 140 of them. Filter the joined view with
`stay_id_str IS NOT NULL` (or the exact ICU identifier system) before casting
`CAST(stay_id_str AS INTEGER)` to the manifest's `stay_id INTEGER`.

### Optional `Patient` view

The canonical output has no `subject_id`, but the subject spine is available
and was verified. If needed, use:

```json
{
  "column": [
    {"path": "getResourceKey()", "name": "patient_key"},
    {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
  ]
}
```

`subject_id_str` is `VARCHAR` and would require `CAST(... AS INTEGER)` in a
final output. Do not emit `subject_id` from `getResourceKey()`.

## Source-column mapping and target types

| Source column / literal | Role in source SQL | FHIR resource and exact path | Canonical alias | Materialized FHIR type | Final vasopressin type / handling |
|---|---|---|---|---|---|
| `itemid` | Row filter `= 222315` | `MedicationAdministration.medication.ofType(CodeableConcept).coding` inside the constrained `forEach`; coding `code` | `item_code` | `VARCHAR` | Filter exact string `'222315'`; source `itemid` is not an output column |
| `stay_id` | Output and comparison key | `MedicationAdministration.context.getReferenceKey(Encounter)` → equality join to `Encounter.getResourceKey()`; then `Encounter.identifier.where(system='.../encounter-icu').value` | `encounter_key`, `stay_id_str` | both `VARCHAR` | `CAST(stay_id_str AS INTEGER)` → `stay_id INTEGER` |
| `linkorderid` | Output payload | No equivalent; ICU `MedicationAdministration.identifier` is absent | none | — | `CAST(NULL AS INTEGER)` → `linkorderid INTEGER` |
| `rateuom` | Exact `CASE` discriminator | `MedicationAdministration.dosage.rateQuantity.unit`; also `...rateQuantity.code` | `rate_unit`, `rate_code` | `VARCHAR` | Compare exact `rate_unit = 'units/min'`; FHIR ETL trims this string, so whitespace-loss is a potential branch discrepancy (zero such demo rows) |
| `rate` | Direct/converted output value | `MedicationAdministration.dosage.rateQuantity.value` | `rate_value` | raw `decimal(32,6)`; ViewDefinition alias `VARCHAR` | Cast alias to `DOUBLE`, apply `CASE`, then `CAST(... AS FLOAT)` → `vaso_rate FLOAT` |
| rate Quantity system | FHIR unit provenance | `(dosage.rate).ofType(Quantity).system` | `rate_system` | `VARCHAR` | Observed `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units`; not an oracle output |
| `amount` | Output value | `MedicationAdministration.dosage.dose.value` | `amount_value` | raw `decimal(32,6)`; ViewDefinition alias `VARCHAR` | Cast alias to `DOUBLE`, then `CAST(... AS FLOAT)` → `vaso_amount FLOAT` |
| `amountuom` | Not selected by source SQL, but contextual unit | `MedicationAdministration.dosage.dose.unit`; also `...dose.code` | `amount_unit`, `amount_code` | `VARCHAR` | Observed `units`; amount unit is not an output column |
| amount Quantity system | FHIR unit provenance | `(dosage.dose).ofType(Quantity).system` | `amount_system` | `VARCHAR` | Observed `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units`; not an oracle output |
| `starttime` | Output and comparison-key component | `(effective).ofType(Period).start` when rate is non-null | `effective_period_start` | `VARCHAR` containing offset-bearing FHIR datetime | `TRY_CAST(effective_period_start AS TIMESTAMP_NTZ)` → `starttime TIMESTAMP` |
| `endtime` | Output interval end | `(effective).ofType(Period).end` when rate is non-null; `(effective).ofType(dateTime)` when rate is null | `effective_period_end`, `effective_datetime` | each `VARCHAR` | `TRY_CAST(COALESCE(effective_period_end,effective_datetime) AS TIMESTAMP_NTZ)` → `endtime TIMESTAMP` |
| `orderid` | Raw PK component `(orderid,itemid)`, not selected | No source-valued FHIR path; ETL uses it inside the opaque `MedicationAdministration.id` | `medadmin_key` is only the opaque resource key | `VARCHAR` | Never parse, regenerate, hash, or invert the resource id; no final output column |
| `subject_id` (raw table, not used by source SQL) | Not selected | `MedicationAdministration.subject.getReferenceKey(Patient)` → `Patient.getResourceKey()`; optional Patient identifier path above | `patient_key`, optional `subject_id_str` | `VARCHAR` | No final output; if used, cast the identifier value to `INTEGER` |

There is no `Medication` resource join for this source query. The
`MedicationAdministration.medication` CodeableConcept carries the itemid
coding directly.

## Confirmed coding discriminator

- Actual served system:
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`.
- Exact served code: `222315`; display: `Vasopressin`.
- Target counts from the constrained coding projection: 55 coding rows,
  55 distinct MedicationAdministration resources. The only source code is
  `itemid = 222315`; there are no terminology translations.
- Overall coding fan-out: 56,535 coding rows / 56,535 distinct resources =
  `1.000`; ICU system = 20,404/20,404 = `1.000`.
- `CodeSystem` is not present in the Delta warehouse (`src.read("CodeSystem")`
  raised `No data found for resource type: CodeSystem`). The system/code must
  therefore be taken from the observed MedicationAdministration coding and
  the ICU ETL, not from a served CodeSystem or `meta.profile`.
- The discriminator is `system + exact code`, never `meta.profile`. The code
  is the ICU `d_items.itemid`; the ICU CodeSystem ETL selects the dimension
  rows with `linksto='inputevents'`, so the target system/code pair is
  sufficient to select the stream in the merged warehouse.

## Effective time, dosage, precision, and datetime behavior

- Target vasopressin demo counts: 55/55 `effective_period_start`, 55/55
  `effective_period_end`, 0/55 `effective_datetime`; all 55 are the Period
  branch. Across the ICU medication system, the probe found 11,038 Period
  resources and 9,366 dateTime resources, with 11,038/20,404 rate values.
- The ETL rule is rate-presence based: non-null source `rate` writes
  `effectivePeriod(start=starttime,end=endtime)`; null source `rate` writes
  `effectiveDateTime=endtime` and omits Period, including its start. The
  final SQL must project both choice variants and coalesce only the end.
- Quantity values are raw `decimal(32,6)`. Pathling's materialized
  ViewDefinition aliases are string-like, so `rate_value` and `amount_value`
  must be explicitly cast before arithmetic and final `FLOAT` output.
- Demo source query stats for `itemid=222315`: 55/55 rate, amount, starttime,
  and endtime non-null; `rateuom='units/hour'` 55/55, `units/min` 0/55;
  `amountuom='units'` 55/55. The source SQL's exact `units/min` branch is
  nevertheless required for the full data and multiplies by `60.0`.
- FHIR datetimes are offset-bearing strings. Use `TIMESTAMP_NTZ`, not an
  offset-aware `TIMESTAMP` conversion, because the offset is an ETL rendering
  of de-identified wall-clock data. The ICU ETL casts source endpoints through
  `TIMESTAMPTZ`; a DST spring-forward-gap source wall time can be irreversibly
  shifted by +1 hour. No such conflict occurred in the demo vasopressin
  sample: source/FHIR starttime keys were 55/55 and endtime was 55/55 exact.

## Joins and oracle check

- `MedicationAdministration.context.getReferenceKey(Encounter)` joined to
  `Encounter.getResourceKey()` for 55/55 target rows; the ICU identifier value
  was non-null for 55/55 joined rows.
- `MedicationAdministration.subject.getReferenceKey(Patient)` joined to
  `Patient.getResourceKey()` for 55/55 target rows; the Patient identifier
  value was non-null for 55/55.
- DuckDB keyed comparison against `mimiciv_icu.inputevents WHERE itemid=222315`
  found 55 source rows, 55 FHIR rows, 55/55 common `(stay_id,starttime)` keys,
  zero source-only rows, zero FHIR-only rows, and no duplicate keys on either
  side. Endtime agreed exactly 55/55. Rate agreed 55/55 within
  `rtol=1e-6, atol=1e-6` (maximum absolute difference
  `4.74945068163e-7`; binary-exact 0/55); amount agreed 55/55 under the same
  tolerance (maximum absolute difference `2.00000000206e-6`; binary-exact
  2/55). Rate and amount units agreed exactly 55/55.

## Gaps and representability bounds

1. **`linkorderid`: not representable, ancillary.** The source output is
   `INTEGER`, but the served ICU MedicationAdministration has no identifier
   field carrying it (0/56,535 resources had a non-empty identifier; the
   target source had linkorderid non-null on 55/55 demo rows). The resource id
   is opaque and cannot be inverted; the ETL's use of `orderid` in UUID
   generation is a forbidden side channel and does not recover linkorderid.
   `linkorderid` is not the manifest key and does not control row inclusion,
   grouping, time carry-forward, or `vaso_rate`; emit typed NULL only for this
   output column.
2. **Raw `orderid`: not representable as a source value, but not a canonical
   output.** It is part of raw `(orderid,itemid)` identity and is used by the
   ETL when constructing the opaque resource id. Equality/grouping by
   `medadmin_key` is permitted; parsing, candidate hashing, hardcoded lookup,
   or UUID inversion is forbidden. The six-column source output does not
   select `orderid`, so this does not by itself change the port's output.
3. **`starttime` on the rate-null branch: absent but branch-identifiable.** On
   exactly the rows where the FHIR discriminator `rate_value` is NULL (the
   `dosage.rateQuantity` is absent), FHIR carries `endtime` as
   `effective_datetime` but carries no Period.start. Emit a typed NULL
   `starttime` on those rows; do not infer it from the opaque id. The demo
   bound is 0/55 rows (all target rows had a rate and Period). If such rows
   occur in full data, the missing value reaches the `(stay_id,starttime)`
   comparison key, so the judge must assess that bounded key coverage, but the
   surviving rate-presence discriminator identifies the affected rows rather
   than making the loss unbounded.
4. **Datetime transformation: not representable only at ETL DST-gap rows.**
   The upstream `TIMESTAMPTZ` cast can normalize a nonexistent New York
   spring-forward wall time by +1 hour. `TIMESTAMP_NTZ` preserves the served
   value but cannot recover the original wall time; the resource id cannot be
   used as a side channel. The demo vasopressin check reached 0/55 such
   conflicts, but the full-data prevalence was not locally available.
5. **Rate-unit trimming: potential branch loss, not observed in demo.** The
   ETL uses `TRIM(rateuom)` while the source SQL compares the raw value exactly
   to `'units/min'`. A raw whitespace-padded unit would be indistinguishable
   after FHIR serialization and could alter the CASE branch; the demo had
   0/55 padded units. Verify this against full raw data if a full mismatch
   attributes to the unit discriminator. No whole-concept block is warranted
   from this bounded, zero-row demo finding.

The source does not use `patientweight`, `amountuom`, status fields, or other
inputevent columns beyond those listed above. `amountuom` is available in the
FHIR dose Quantity but is not an output or discriminator; absent
`patientweight` therefore does not affect this concept.

## Files and probe provenance

- Canonical source: `mimic-iv/concepts/medication/vasopressin.sql`.
- Established notes read: `mimic-iv/concepts_fhir/MIMIC_NOTES.md`.
- Provisional sibling fragments read: `MIMIC_NOTES.d/dobutamine.md`,
  `dopamine.md`, `epinephrine.md`, `milrinone.md`, `norepinephrine.md`,
  `phenylephrine.md`, plus `MIMIC_NOTES.d/icustay_times.md` and `README.md`.
- ETL read: `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql`.
- Canonical ViewDefinition structure read:
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- Own append-only fragment: `mimic-iv/concepts_fhir/MIMIC_NOTES.d/vasopressin.md`.
