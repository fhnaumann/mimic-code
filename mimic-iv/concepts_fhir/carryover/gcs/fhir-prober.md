# FHIR prober mapping — `gcs`

**Concept:** `measurement/gcs`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/gcs/source-analyst.md`  
**Probe date:** 2026-08-11  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only  
**No stale NDJSON was read.**

## Resource and stream mapping

`mimiciv_icu.chartevents` maps to the `Observation` resource, specifically the
chartevents coding stream. The ETL statement
`/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:24-38`
reads the source table, removes NULL `value` rows, and creates one Observation
per remaining chartevents row (apart from its hard-coded duplicate exclusion).
The resource is confirmed by the authoritative Delta `Observation` schema and
by the target coding system below.

The discriminator is **system plus exact string code**, never `meta.profile`:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
codes  = "223900", "223901", "220739"
```

The three exact code/display/count results in Delta were:

| Source `itemid` | FHIR `Coding.code` | FHIR display | System | coding rows | distinct resources |
|---:|---|---|---|---:|---:|
| 220739 | `"220739"` | `GCS - Eye Opening` | `mimic-chartevents-d-items` | 3,274 | 3,274 |
| 223900 | `"223900"` | `GCS - Verbal Response` | `mimic-chartevents-d-items` | 3,266 | 3,266 |
| 223901 | `"223901"` | `GCS - Motor Response` | `mimic-chartevents-d-items` | 3,251 | 3,251 |

The exact-code query found no other system for any of the three codes. The
authoritative Delta has no `CodeSystem` resource (`src.read('CodeSystem')`
raised `No data found`), so this confirmation comes from served Observation
codings and the ETL, not terminology expansion. The DuckDB `d_items` rows are
one-per-item (`3` rows, `3` distinct itemids), all `linksto='chartevents'`,
with the labels shown above. This is enough to separate these GCS items: their
system is the chartevents-specific system, unlike the shared `mimic-d-items`
system used by outputevents and datetimeevents; exact code remains part of the
rule because `d_items.itemid` is the global dimension key with one `linksto`
value per item.

Coding cardinality was checked with a projection over `forEach: "code.coding"`:

* all chartevents-system codings: **668,862 / 668,862 resources = 1.000**;
* the three-code target: **9,791 / 9,791 resources = 1.000**;
* each individual code also had a ratio of **1.000**.

Use a constrained coding group and project these canonical columns:

```text
forEach: code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')
{ "path": "code",    "name": "item_code" }
{ "path": "system",  "name": "code_system" }
{ "path": "display", "name": "code_display" }
```

Apply the exact three string codes after this system-constrained projection (or
include the exact-code disjunction inside the `where`). Do not cast arbitrary
Observation codes before the system/code filter.

## Canonical source-column → FHIRPath mapping

The UUID/reference columns below are join support, not the output MIMIC IDs.
FHIR choice aliases are materialized by Pathling as strings even where the FHIR
element is decimal or dateTime; the implementer must cast to the manifest type
in the final SQL.

| Source column / final output | Canonical `{path, name}` | FHIR type | Delta population / required final type |
|---|---|---|---|
| `subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` plus Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key string, then `Identifier.value` string | Observation reference, Patient join, and identifier value were 9,791/9,791 non-null; final `CAST(subject_id_str AS INTEGER)` → manifest `INTEGER` |
| `stay_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` plus ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` key string, then `Identifier.value` string | Observation reference, Encounter join, and ICU identifier were 9,791/9,791 non-null; final `CAST(stay_id_str AS INTEGER)` → manifest `INTEGER` |
| `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `Observation.effective[x]` = `dateTime`; materialized `STRING` with ISO offset | 9,791/9,791 non-null; parse with `CAST(effective_datetime AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP`; do not offset-convert |
| `itemid` (filter/pivot discriminator) | In the constrained coding `forEach`: `{ "path": "code", "name": "item_code" }` and `{ "path": "system", "name": "code_system" }` | `Coding.code` / `Coding.system`, both strings | Exact target counts above; cast/filter only after system plus exact string code |
| `d_items.label` (not a source output) | In the coding `forEach`: `{ "path": "display", "name": "code_display" }` | `Coding.display` string | 9,791/9,791 populated and agrees with the three DuckDB `d_items.label` values; no output column |
| `valuenum` → component values | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` decimal; raw Delta `DecimalType(32,6)`, materialized alias `STRING` | 9,791/9,791 target rows; cast to `FLOAT` for `gcs_motor`, `gcs_verbal`, `gcs_eyes` |
| `valueuom` (not selected by source SQL) | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | `Quantity.unit` string | 0/9,791 populated; source `valueuom` was NULL for all 9,791 rows; informational only |
| exact source `value` text when it is a string | `{ "path": "(value).ofType(string)", "name": "value_string" }` | `value[x]` = `string` | 0/9,791 populated for these numeric GCS items; do not expect the ETT text here |
| resource identity (support only) | `{ "path": "getResourceKey()", "name": "observation_key" }` | Observation resource key string (`Observation/<UUID>`) | 9,791/9,791 non-null and distinct; not an output `stay_id`, `subject_id`, or natural key |

The raw Observation schema also exposes `effectiveInstant` and
`effectivePeriod`; the target probe found `effectiveInstant` 0/9,791 and
Period start/end 0/9,791. The GCS view therefore needs only the dateTime
variant; there is no target-side effective-choice COALESCE.

The output natural key is the oracle key **`(stay_id, charttime)`**, not
`Observation.getResourceKey()` and not `itemid`. The full oracle manifest says
`keyed_join`, key `['stay_id', 'charttime']`, row count 1,637,763, and output
types `INTEGER, INTEGER, TIMESTAMP, FLOAT, FLOAT, FLOAT, FLOAT, INTEGER`.
The candidate must pivot the three code streams at `(stay_id, charttime)` and
must not emit `itemid`, `rn`, or `observation_key`.

## Exact sentinel and value-variant finding

The source literal is exactly `value = 'No Response-ETT'` for `itemid=223900`.
DuckDB found:

* 1,348 exact sentinel rows;
* every one had `valuenum=1`, not zero;
* the other 78 verbal rows with `value='No Response'` also had `valuenum=1`;
* all 3,266 verbal rows had non-NULL `valuenum`.

The served ETL at `fhir_observation_chartevents.sql:69-80` writes
`valueQuantity` whenever `valuenum IS NOT NULL` and writes `valueString` only
when `valuenum IS NULL`. Consequently, for code `223900` Delta has
`quantity_value` on 3,266/3,266 rows, `value_string` on 0/3,266, and Quantity
value `1` on 1,426 rows (the 1,348 sentinel rows plus the 78 `No Response`
rows). The exact sentinel is therefore **not present at a direct FHIR value
path**, and `quantity_value=1` is not a safe sentinel discriminator.

There is an ETL-specific equality witness: lines 20-23 of the ETL create the
Observation UUID from `stay_id-charttime-itemid-value` before datetime
serialization. Recreating the UUIDv5 namespace chain from
`mimic-fhir/sql/fhir_etl/uuid_namespace.sql:7-32` and the exact source string
matched the served `Observation.getResourceKey()` for **9,791/9,791** GCS
rows, including the 1,348 sentinel rows. Thus the sentinel is **absent from a
normal FHIR value path but derivable only by finite candidate enumeration over
the ETL UUID input** (and is not a general FHIRPath mapping). Do not infer it
from Quantity 1. If the implementer does not use this ETL-key witness, the
sentinel/`gcs_unable` distinction is an intrinsic representation gap and must
not be replaced with a heuristic.

The final source-derived demo shape, checked with an equivalent DuckDB CTE,
was 3,279 `(stay_id, charttime)` rows. Null/non-null counts were:

| Output | total | non-null |
|---|---:|---:|
| `subject_id`, `stay_id`, `charttime`, `gcs`, `gcs_unable` | 3,279 | 3,279 each |
| `gcs_motor` | 3,279 | 3,265 |
| `gcs_verbal` | 3,279 | 3,275 |
| `gcs_eyes` | 3,279 | 3,278 |

`gcs_unable=1` occurred on 1,348 current sentinel rows; the carried component
`gcs_verbal=0` occurred on 1,352 output rows because the source calculation can
carry a preceding sentinel component. `gcs` itself is derived, not a FHIR
element: reproduce the analyst's six-hour previous-row logic, exact sentinel
branch, defaults (motor 6, verbal 5, eyes 4), and scalar ETT result 15.

## Cardinality, null, and oracle checks

The embedded Pathling target and read-only DuckDB source checks were:

| Check | Result |
|---|---:|
| Source selected rows (`itemid IN (...)`) | 9,791 |
| Source selected rows with non-NULL `value` | 9,791 |
| Source selected rows with NULL `value` | 0 |
| FHIR target coding rows | 9,791 |
| FHIR distinct Observation keys | 9,791 |
| Source `(stay_id, charttime)` groups | 3,279 |
| Source repeated `(stay_id, charttime, itemid)` groups | 0 in demo |
| Source repeated `(stay_id, charttime)` groups | 3,268, containing 9,780 rows |
| FHIR/source key-group count agreement | 9,791/9,791 |
| FHIR/source exact `(subject_id, stay_id, charttime, itemid)` tuples | 9,791/9,791 |
| Quantity/value-kind agreement | 9,791/9,791 |
| Quantity numeric agreement within `1e-6` | 9,791/9,791 |
| Effective wall-clock agreement after local `TIMESTAMP_NTZ` parsing | 9,791/9,791 |
| Patient identifier and ICU Encounter identifier joins | 9,791/9,791 each |

The hard-coded ETL duplicate exclusion was checked directly in DuckDB for
`stay_id=34934165`, `charttime='2151-10-03 05:14:00'`: it returned 0 rows and
0 GCS rows, so it does not affect this demo target. The shared chartevents
NULL-value omission is also not exercised by these three demo itemids. On full
data, the canonical query retains NULL-`value` rows but the ETL does not, so
those rows are absent from FHIR rather than NULL-valued Observations.

The ETL casts source `charttime` through `TIMESTAMPTZ` at line 9 and writes it
as `effectiveDateTime` at line 67. The demo GCS target had no resulting
datetime disagreement, but the shared DST-gap note still applies: parse the
served offset-bearing dateTime as a MIMIC wall clock with `TIMESTAMP_NTZ`, and
do not use an offset-aware Spark cast. A DST-gap source time can be irreversibly
normalised by the upstream ETL; the UUID equality witness is separate from the
effective-time value.

## Gaps

* **Source `value` / exact `No Response-ETT`: absent at a direct FHIR value
  path, but ETL-key-derivable for the known finite labels.** The served value
  loses the text and conflates the sentinel with `No Response` at Quantity 1.
  UUIDv5 re-generation matched all 9,791 demo resources and can identify the
  sentinel when the original wall-clock/ETL input candidates are enumerated;
  there is no standard FHIRPath that decodes this. A quantity-1 heuristic is
  measured to be non-exact (1,348 sentinel + 78 non-sentinel rows) and must not
  be used.
* **Selected source rows with NULL `value`: not representable as an
  Observation row in this ETL.** The ETL filters them before resource creation.
  This is not exercised by the demo GCS itemids (0 source NULL rows), but the
  canonical source SQL has no such filter; preserve the candidate's declared
  shape and document any full-data missing-row gap rather than inventing a
  value.
* **`valueuom`: no gap for this concept.** It is not selected by the source SQL,
  and both source and FHIR were NULL on all 9,791 target events.
* **Raw event identity:** not an output requirement. The source query folds
  events to `(stay_id, charttime)` and uses `MAX` per item. The FHIR resource
  UUID is available only as support; never substitute it for the manifest key.

## Notes/fragments and evidence provenance

Read before probing: `AGENTS.md`, `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`,
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, the canonical
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`,
`README.md`, `blood_differential.md`, `cardiac_marker.md`,
`chemistry.md`, `code_status.md`, `coagulation.md`,
`complete_blood_count.md`, `crrt.md`, `dobutamine.md`, `dopamine.md`,
`epinephrine.md`, and `gcs.md`.

The following established notes changed this mapping decision:

* the Delta-over-NDJSON note required all code/count checks to use embedded
  Pathling over Delta;
* the coding-system/profile policy and Observation profile-version note required
  system plus exact code, never `meta.profile`;
* the identifier-spine and ICU Encounter-system notes required the two UUID
  reference joins plus `identifier.value` string casts for `subject_id` and
  `stay_id`;
* the datetime note required `TIMESTAMP_NTZ` wall-clock parsing;
* the categorical-chartevents note required probing both `valueString` and
  Quantity rather than assuming a CodeableConcept; this probe sharpened that
  GCS's numeric sentinel is not `valueString` at all.

The provisional `gcs.md` NULL-value claim was checked against the same ETL
statement and against DuckDB's 0/9,791 selected NULL rows; it is true as a
dataset-wide ETL rule but unexercised for GCS in this demo. The `crrt.md`
repeat/DST leads and `code_status.md` duplicate/DST leads were read but not
re-used as GCS counts; the GCS-specific repeat and datetime checks above were
run independently. `cardiac_marker.md`'s system-before-integer-cast safeguard
was independently corroborated by the exact string coding probe. The other
medication/lab fragment claims were read and were not relevant to this
Observation-chartevents mapping; no unverified fragment was promoted as fact.

Appended to the owned fragment `mimic-iv/concepts_fhir/MIMIC_NOTES.d/gcs.md`:
**“Numeric chartevents discard source text even when `value` is non-NULL.”**
This is dataset-wide because it is the unconditional ETL branch at lines
69-80, although the measured sentinel collision is GCS-specific evidence.

No ViewDefinition, SQL, or attempt artifact was created. This reusable mapping
file and the owned notes fragment are the artifacts produced by this stage.
