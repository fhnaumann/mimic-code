# FHIR mapping: `nsaid`

**Source analysis:** `mimic-iv/concepts_fhir/carryover/nsaid/source-analyst.md`  
**Canonical SQL:** `mimic-iv/concepts/medication/nsaid.sql`  
**Probe date:** 2026-08-13  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only

## Result

`mimiciv_hosp.prescriptions` is represented by the pharmacy-backed
`MedicationRequest` stream, with the prescription drug recovered through
referenced `Medication` resources. There are two required drug branches:

1. A direct request reference points to a name-bearing `Medication`.
2. A request for a multi-drug pharmacy group points to a medication-mix
   `Medication`; each repeated `ingredient.itemReference` points to a
   component name-bearing `Medication`.

The final query must use `UNION ALL` for these branches and must not use
`DISTINCT`. The direct branch is one row per pharmacy-backed request; the mix
branch is one row per repeated ingredient reference. This preserves the
source prescription-row multiplicity. The demo NSAID cohort happens to have
202 singleton pharmacy groups and therefore exercises only the direct branch,
but the mix branch is required for full data.

The source output named `nsaid` is the original free-text `prescriptions.drug`
value. It is not a FHIR code and must not be obtained from
`Medication.code.coding.code`, whose ETL priority is NDC, formulary drug code,
then medication name.

## Canonical ViewDefinition mappings

The snippets use the canonical `select[].column[]` and `select[].forEach`
shape from `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
These are mappings only; no attempt ViewDefinition was authored.

### MedicationRequest spine

```json
{
  "resource": "MedicationRequest",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "medication_request_key" },
      { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
      { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" },
      { "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" },
      { "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" },
      { "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }
    ]
  }]
}
```

`pharmacy_id_str` is a support/discriminator column, not a final output
column. Requiring it to be non-null selects the 15,225 prescription-backed
requests and excludes the 2,327 POE-only requests. The request's
`medicationReference` is present on all 15,225 pharmacy-backed requests.

### Name-bearing Medication: direct and mix component target

```json
{
  "resource": "Medication",
  "select": [
    { "column": [
      { "path": "getResourceKey()", "name": "medication_key" }
    ]},
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name')",
      "column": [
        { "path": "system", "name": "drug_system" },
        { "path": "value", "name": "drug_name" }
      ]
    }
  ]
}
```

The direct branch joins `mr.medication_key` to `medication_key`. The mix
branch joins each ingredient component key to the same name-bearing view.
`drug_name` is the exact source drug string; apply the source `UPPER(drug)`
substring predicates to `UPPER(drug_name)`.

### Medication-mix identifier and ingredient references

The mix identifier is useful to establish the resource branch, but it is not
the source drug value. Do not parse the identifier string. Project ingredient
references instead:

```json
{
  "resource": "Medication",
  "select": [
    { "column": [
      { "path": "getResourceKey()", "name": "mix_key" }
    ]},
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-mix')",
      "column": [
        { "path": "system", "name": "mix_system" },
        { "path": "value", "name": "mix_identifier" }
      ]
    }
  ]
}
```

```json
{
  "resource": "Medication",
  "select": [
    { "column": [
      { "path": "getResourceKey()", "name": "mix_key" }
    ]},
    {
      "forEach": "ingredient",
      "column": [
        { "path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key" }
      ]
    }
  ]
}
```

The full FHIR element is `Medication.ingredient.itemReference`; the
materialized Pathling path inside `forEach: "ingredient"` is
`itemReference.getReferenceKey(Medication)`. Preserve every repeated
ingredient. The `mix_identifier` is not an allowed source-drug recovery path.

### Patient and hospital Encounter identifier joins

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

```json
{
  "resource": "Encounter",
  "select": [{
    "column": [
      { "path": "getResourceKey()", "name": "encounter_key" },
      { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }
    ]
  }]
}
```

Join `MedicationRequest.patient_key` to `Patient.patient_key` and
`MedicationRequest.encounter_key` to `Encounter.encounter_key`. Filter the
Encounter view with `hadm_id_str IS NOT NULL`; do not use `Encounter.class`.
The final SQL must cast `subject_id_str` and `hadm_id_str` to `INTEGER`.

## Source-column to FHIRPath mapping and types

FHIR identifiers and dateTime aliases are strings in the materialized
Pathling views. The UUID/reference keys are opaque join-only strings. They
must never be parsed, regenerated, hardcoded, or used to infer a source value.

| Source column | Canonical FHIRPath mapping (`{path, name}`) | FHIR/logical type | Materialized type | Required final output/type |
|---|---|---|---|---|
| `prescriptions.subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }`, then Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference` plus `Identifier.value` string | `StringType()` | `CAST(subject_id_str AS INTEGER)` → `INTEGER` |
| `prescriptions.hadm_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }`, then hospital Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" }` | `Reference` plus `Identifier.value` string | `StringType()` | `CAST(hadm_id_str AS INTEGER)` → `INTEGER` |
| `prescriptions.drug`, direct request | `{ "path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key" }`, then name Medication `{ "path": "value", "name": "drug_name" }` under the name-identifier `forEach` | `Reference` plus `Identifier.value` string | `StringType()` | `CAST(drug_name AS VARCHAR(255))` → `VARCHAR` |
| `prescriptions.drug`, mix ingredient | `{ "path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key" }` under `forEach: "ingredient"`, then name Medication `{ "path": "value", "name": "drug_name" }` | repeated `Reference` plus `Identifier.value` string | `StringType()` | `CAST(drug_name AS VARCHAR(255))` → `VARCHAR` |
| `prescriptions.starttime` | `{ "path": "dispenseRequest.validityPeriod.start", "name": "starttime_str" }` | `Period.start` `dateTime` | `StringType()` with ISO offset | `TRY_CAST(starttime_str AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP` |
| `prescriptions.stoptime` | `{ "path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str" }` | `Period.end` `dateTime` | `StringType()` with ISO offset | `TRY_CAST(stoptime_str AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP` |
| `prescriptions.pharmacy_id` (support only) | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid').value", "name": "pharmacy_id_str" }` | `Identifier.value` string | `StringType()` | support-only `VARCHAR`; do not emit |
| source row identity support | `{ "path": "getResourceKey()", "name": "medication_request_key" }` | FHIR resource key, opaque UUID string | `StringType()` | join/provenance only; never output |

The final output mapping is therefore:

```text
prescriptions.subject_id -> {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"}
prescriptions.hadm_id    -> {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"}
prescriptions.drug       -> {"path": "medicationReference.getReferenceKey(Medication)", "name": "medication_key"}
prescriptions.drug       -> {"path": "itemReference.getReferenceKey(Medication)", "name": "ingredient_medication_key"}  [mix ingredient branch]
prescriptions.starttime  -> {"path": "dispenseRequest.validityPeriod.start", "name": "starttime_str"}
prescriptions.stoptime   -> {"path": "dispenseRequest.validityPeriod.end", "name": "stoptime_str"}
```

The resolved `drug_name` is emitted as output column `nsaid`; it is not a
resource key or a medication code.

## Delta population, identifiers, and multiplicity probes

All counts in this section were obtained from materialized ViewDefinitions or
raw Delta projections over the authoritative demo warehouse, using
`count(*)` versus `count(non_null_column)`.

| Probe | Rows total | Non-null/resolved |
|---|---:|---:|
| `MedicationRequest` | 17,552 | `patient_key` 17,552; `encounter_key` 17,552 |
| pharmacy request identifier (`phid`) | 17,552 | 15,225 |
| pharmacy request medication reference | 17,552 | 15,225 |
| validity start | 17,552 | 14,574 |
| validity end | 17,552 | 14,574 |
| `Patient` patient identifier | 100 | 100 |
| `Encounter` hospital identifier | 637 | 275 |
| name-bearing `Medication` | 1,480 | name identifier/value 1,480/1,480 |
| mix `Medication` | 314 | mix identifier 314/314 |
| mix ingredient references | 634 | 634/634; all resolve to name Medications |

The request branch counts are 12,382 direct and 2,843 mix requests. Expanding
the full pharmacy-backed graph produces 18,087 rows: 12,382 direct plus 5,705
mix ingredient rows. The mix reference ratio is 634/314 = **2.019** per mix
resource (310 resources have two ingredients, two have three, and two have
four). No `DISTINCT` may be applied after this expansion.

The name identifier ratio is 1,480/1,480 = **1.000** per name-bearing
Medication. The mix identifier ratio is 314/314 = **1.000**. The pharmacy
identifier ratio is 15,225/15,225 = **1.000** per pharmacy-backed request.

The served direct/component `Medication.code.coding` projection has one
coding per resource: 1,480 coding rows / 1,480 resources = **1.000**. Its
systems are 1,402 NDC, 72 formulary-drug-code, and 6 medication-name codings;
all 1,480 displays are null. This coding is not the NSAID discriminator.

The observed exact identifier/coding systems are:

```text
drug name identifier:
  http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name
medication-mix identifier:
  http://mimic.mit.edu/fhir/mimic/identifier/medication-mix
pharmacy-backed MedicationRequest identifier:
  http://mimic.mit.edu/fhir/mimic/identifier/medication-request-phid
POE-only MedicationRequest identifier (exclude):
  http://mimic.mit.edu/fhir/mimic/identifier/medication-request-poe
Patient identifier:
  http://mimic.mit.edu/fhir/mimic/identifier/patient
hospital Encounter identifier:
  http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp
```

Discrimination is by the exact identifier system plus value where applicable,
and by the exact source free-text predicate. `meta.profile` is not used.

## Literal filter confirmation

There is no formal numeric/code filter in `nsaid.sql`. The source specification
is the following 20 exact `UPPER(drug) LIKE '%TOKEN%'` literals. Counts are
source DuckDB rows and expanded FHIR name rows. Zero is a served-demo count,
not permission to remove a source literal.

| Source literal | Oracle rows | FHIR rows |
|---|---:|---:|
| `ASPIRIN` | 170 | 170 |
| `BROMFENAC` | 0 | 0 |
| `CELECOXIB` | 0 | 0 |
| `DICLOFENAC` | 0 | 0 |
| `DIFLUNISAL` | 0 | 0 |
| `ETODOLAC` | 0 | 0 |
| `FENOPROFEN` | 0 | 0 |
| `FLURBIPROFEN` | 0 | 0 |
| `IBUPROFEN` | 26 | 26 |
| `INDOMETHACIN` | 1 | 1 |
| `KETOPROFEN` | 0 | 0 |
| `MEFENAMIC ACID` | 0 | 0 |
| `MELOXICAM` | 0 | 0 |
| `NABUMETONE` | 0 | 0 |
| `NAPROXEN` | 5 | 5 |
| `NEPAFENAC` | 0 | 0 |
| `OXAPROZIN` | 0 | 0 |
| `PIROXICAM` | 0 | 0 |
| `SULINDAC` | 0 | 0 |
| `TOLMETIN` | 0 | 0 |
| **OR of predicates** | **202** | **202** |

All 202 demo NSAID FHIR rows use the name identifier system above. Their
resolved names are `Aspirin`, `Aspirin EC`, `Ibuprofen`, `Naproxen`,
`Indomethacin`, `Aspirin (Buffered)`, `Ibuprofen Suspension`, and
`Aspirin 81 mg `; the exact source spelling is retained. The demo NSAID rows
are all direct branch rows (202/202); the zero mix count is cohort-specific,
not a reason to omit the mix branch.

## Oracle agreement and row multiplicity

The source NSAID target has 202 rows and 202 distinct `(pharmacy_id, drug)`
groups. The FHIR expansion has 202 NSAID rows, all in the direct branch.
Joining through the support pharmacy identifier, subject identifier, hospital
Encounter identifier, and resolved name gave exact agreement on the
identifier/name portion for 202/202 rows. The source visible output has only
200 distinct five-column tuples among 202 rows, so duplicate output tuples are
real and must not be removed. The full oracle manifest confirms that `nsaid`
is unkeyed and compared as a `full_tuple_multiset` with 235,678 full-data rows.

This concept does not emit `pharmacy_id` or `drug_type`, but the FHIR request
identifier and repeated mix ingredients must still be used internally so
source-row multiplicity is not lost. Do not use a resource UUID as a surrogate
source key and do not parse it.

## Validity-period omissions and datetime behavior

For the 202 demo NSAID source rows:

- `starttime` and `stoptime` are non-null on 202/202;
- 192/202 are complete and non-reversed (`starttime <= stoptime`);
- 10/202 are reversed;
- 0/202 are incomplete.

The FHIR expansion carries both validity endpoints on 192/202 rows and
neither endpoint on 10/202 rows. Comparing source wall-clock strings to the
served FHIR values after a `TIMESTAMP_NTZ` wall-clock cast gave exact agreement
for 192/192 valid rows. The ten omitted reversed intervals account for the
remaining 10 source-only / 10 candidate-only timestamp tuples; no source time
was fabricated.

The upstream ETL reads grouped prescription times through
`CAST(... AS TIMESTAMPTZ)` at `mimic-fhir/sql/fhir_medication_request.sql:43-44`
and writes `dispenseRequest.validityPeriod` only when both coalesced endpoints
exist and start is no later than stop at lines 172-177. `authoredOn` is pharmacy
entry time (`entertime`), is populated on the request stream, and is not a
substitute for either source endpoint.

ViewDefinition aliases for the validity endpoints are strings containing an
ISO-8601 offset. The implementer must cast each alias with
`TRY_CAST(... AS TIMESTAMP_NTZ)`, not an offset-aware `TIMESTAMP` cast. The
offset is not a meaningful instant for these de-identified wall-clock values.

The demo NSAID target had no source endpoint in the 02:xx DST-gap hour, so no
NSAID-specific DST conflict was observed locally. The upstream `TIMESTAMPTZ`
operation is nevertheless a full-data risk: a nonexistent New York spring-
forward 02:xx wall time is serialized as 03:xx, and the original wall time is
not recoverable from the served validity period. The existing prescription
probes in the curated notes and medication fragments confirm this behavior.
Do not attempt to recover it from any resource id.

MedicationRequest is grouped by `pharmacy_id` upstream. In the demo, every
NSAID pharmacy group is a singleton, so the grouped request values are exact.
For a full-data pharmacy group containing multiple source drugs, the mix
ingredient branch preserves drug multiplicity but the request has only one
grouped validity interval (ETL `MAX` values); Medication and its ingredients do
not carry per-ingredient start/stop values. If source times differ within such
a group, the individual source endpoint values are not representable by a
FHIR query. This was not exercised by the demo NSAID cohort and must not be
silently solved with `authoredOn` or an inferred time.

## Gaps and essentiality

### Invalid or incomplete source validity intervals — absent and not representable

`MedicationRequest.dispenseRequest.validityPeriod.start/end` is absent for
invalid or incomplete grouped intervals. No alternate served element carries
the original endpoints: `authoredOn` is unrelated pharmacy entry time, and the
Medication and mix resources carry names/ingredients only. The ten reversed
demo NSAID intervals therefore require typed NULL timestamps in a port. No
approximation is warranted.

This loss does not change NSAID row inclusion in `nsaid.sql`, and the source
query has no temporal carry-forward or time-window predicate. It is potentially
essential to the exact clinically meaningful interval output because the
concept emits both endpoints. If the full-data affected population is material,
the whole concept should be presented to the equivalence judge rather than
publishing fabricated endpoint values; the prober does not make the terminal
judge decision.

### Prescription grouping — potentially absent per-row timing in multi-drug groups

The FHIR request is pharmacy-group grain while the source is prescription-row
grain. Ingredients preserve repeated drug rows, but no FHIR path preserves a
different validity interval per ingredient. The demo NSAID cohort has 202/202
singleton groups, so this is not an observed NSAID discrepancy here. In full
data, differing per-row times within an NSAID-containing pharmacy group would
be absent and not representable, and could change a clinically meaningful
`starttime`/`stoptime` output. It does not by itself change the source
classifier's inclusion rule. Do not infer a time from the mix identifier or an
opaque resource id.

### `drug_type` — absent and not representable, but not used by this concept

The served Medication/medication-mix graph has no `prescriptions.drug_type`
element. The mix ETL uses it only to order ingredients (`MAIN`/`BASE`/
`ADDITIVE`); it does not serialize the type. `nsaid.sql` neither filters nor
outputs `drug_type`, so this is ancillary for this concept. Repeated ingredient
references still preserve source-row multiplicity. Do not claim that the
absence reproduces a source `drug_type` value.

### No gap for drug, subject, admission, or demo multiplicity

The source drug text is carried by the name identifier, subject/admission
values are carried by Patient/Encounter identifier values, and the demo
source/FHIR NSAID identifier/name rows agree 202/202. Direct and mix branches
are both representable; the mix branch is required for full-data multiplicity.

## Curated notes and provisional fragments

The following curated `MIMIC_NOTES.md` entries changed this mapping decision:

- **“MIMIC ids live in `identifier.value` as STRINGs — `getResourceKey()` is a UUID”**: subject and admission IDs come from the Patient and hospital Encounter identifier systems and are cast only at the final output boundary; UUID keys remain join-only.
- **“Prescription Medication.code prefers NDC/formulary; the source drug name is in an identifier”**: `prescriptions.drug` maps to the exact medication-name identifier value, with both direct and ingredient branches.
- **“Prescription route and Medication code displays are null”**: code/display cannot be used as a drug-name fallback; this concept uses the name identifier and does not emit route.
- **“MedicationRequest omits invalid or incomplete prescription validity periods”**: validity paths are nullable and `authoredOn` is not a substitute.
- **“FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ, never to TIMESTAMP”** and its DST-gap continuation: preserve the served wall clock and do not attempt id-based recovery.
- **“Encounter has three identifier systems — class discriminates none of them”**: the hospital Encounter identifier system is the stream filter for `hadm_id`.
- **“Essential source loss blocks the whole derived concept”** and the opaque-id rule: no identifier reconstruction is allowed, and endpoint loss must be surfaced rather than hidden.

I read `MIMIC_NOTES.d/README.md` and every existing fragment returned by the
authoritative glob: `arb.md`, `blood_differential.md`, `cardiac_marker.md`,
`chemistry.md`, `code_status.md`, `coagulation.md`,
`complete_blood_count.md`, `crrt.md`, `dobutamine.md`, `dopamine.md`,
`epinephrine.md`, `gcs.md`, `height.md`, `icp.md`, `icustay_detail.md`,
`icustay_times.md`, `invasive_line.md`, `kdigo_creatinine.md`, `milrinone.md`,
`neuroblock.md`, and `norepinephrine.md`. There was no `nsaid.md` fragment
when probing. The medication leads in `arb.md`, `acei` carryover, and
`antibiotic` evidence were independently checked against the same Delta and
DuckDB; unrelated ICU/lab fragment claims were read as provisional leads but
did not affect this prescription mapping and were not re-verified as claims.

No new dataset/IG-wide quirk was discovered beyond the facts already in
curated `MIMIC_NOTES.md`, so no section was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/nsaid.md`.

## Evidence and artifacts

- Read `AGENTS.md`, `fhir-mapping/SKILL.md`, the source analysis, canonical SQL,
  canonical ViewDefinition reference, curated notes, all existing notes
  fragments, prescription Medication ETL SQL, medication-mix ETL SQL, and
  MedicationRequest ETL SQL.
- Probed the authoritative Delta with embedded Pathling/Spark for resource
  schemas, identifier systems, request/name/mix/ingredient views, populations,
  and multiplicity. No live Pathling server was used.
- Checked the demo DuckDB oracle for all 20 literal counts, source null/time
  status, visible duplicate tuples, pharmacy grouping, and source-to-FHIR
  agreement. The NSAID name/identifier portion agreed 202/202; valid endpoint
  values agreed 192/192; 10 reversed intervals were represented as missing
  validity endpoints.
- No attempt ViewDefinition or `concept.sql` was authored. This carryover file
  is the reusable mapping artifact.
