# FHIR prober mapping — `gcs` (fresh, 2026-08-13)

**Concept:** `measurement/gcs`  
**Source analysis:** `mimic-iv/concepts_fhir/carryover/gcs/source-analyst.md`  
**Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`  
**Engine:** embedded Pathling 9.6.0 on Spark 4.0.2  
**Demo oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, DuckDB read-only  
**No stale NDJSON or live Pathling server was used.**

## Non-negotiable identity prohibition

`Observation.getResourceKey()` / `Observation.id` is opaque resource identity.
It may be retained for equality joins, deduplication, and provenance, but it
**must not** be parsed, regenerated, enumerated, hardcoded, or compared with
guessed source values to recover either `charttime` or the source label
`No Response-ETT`. This explicitly forbids UUIDv5/ETL-UUID recovery of the
discarded label and of pre-normalisation charttime. The only charttime mapping
is the served `Observation.effectiveDateTime` value. The prior carryover's
UUID-witness mapping is invalidated and is not part of this mapping.

## Resource and stream mapping

`mimiciv_icu.chartevents` maps to FHIR `Observation`, specifically the
chartevents coding stream. The ETL source is
`/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_chartevents.sql:24-38`.
It removes source rows with NULL `value` and one hard-coded duplicate tuple
before creating resources. The authoritative Delta Observation schema and the
served coding counts confirm this resource mapping.

The discriminator is **`code.coding.system` plus exact string code**, never
`meta.profile`:

```text
system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items
codes  = "223900", "223901", "220739"
```

The authoritative Delta code results were:

| Source `itemid` | FHIR `Coding.code` | FHIR `Coding.display` | coding rows | distinct resources |
|---:|---|---|---:|---:|
| 220739 | `"220739"` | `GCS - Eye Opening` | 3,274 | 3,274 |
| 223900 | `"223900"` | `GCS - Verbal Response` | 3,266 | 3,266 |
| 223901 | `"223901"` | `GCS - Motor Response` | 3,251 | 3,251 |

No other system was observed for these exact codes. The demo warehouse has no
served `CodeSystem` resource, so the system/code confirmation is from the
served Observation codings, ETL SQL, and the DuckDB `d_items` dimension. The
three `d_items` rows are unique and all have `linksto='chartevents'`. This
system plus exact code rule remains safe against the shared `mimic-d-items`
system used by outputevents/datetimeevents; the global `d_items.itemid` has one
`linksto` per item.

Use a constrained coding group:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" },
    { "path": "display", "name": "code_display" }
  ]
}
```

The coding-per-resource ratio is **1.000** for all chartevents-system codings
(668,862 / 668,862) and for the GCS target (9,791 / 9,791). Each target code
also has ratio 1.000. Filter on the system and exact string code before any
integer cast.

## Canonical source-column → FHIRPath mapping

The UUID/reference columns are join support, not output MIMIC IDs. Pathling
materializes the Quantity and dateTime aliases as strings in this projection;
the implementer must cast them to the manifest types in final SQL.

| Source column / output | Canonical `{path, name}` | FHIR type | Probe result / required output type |
|---|---|---|---|
| `subject_id` | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` plus Patient `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` | `Reference(Patient)` key string; `Identifier.value` string | 9,791/9,791 reference and identifier values populated; join then `CAST(subject_id_str AS INTEGER)` → `INTEGER` |
| `stay_id` | `{ "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key" }` plus ICU Encounter `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | `Reference(Encounter)` key string; `Identifier.value` string | 9,791/9,791 reference values populated; ICU Encounter identifier join 9,791/9,791; `CAST(stay_id_str AS INTEGER)` → `INTEGER` |
| `charttime` | `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }` | `Observation.effective[x]` `dateTime`; materialized `STRING` with ISO offset | 9,791/9,791 populated; `CAST(effective_datetime AS TIMESTAMP_NTZ)` → manifest `TIMESTAMP`; do not offset-convert |
| `itemid` | In constrained coding group: `{ "path": "code", "name": "item_code" }` | `Coding.code` string | Exact codes `223900`, `223901`, `220739`; cast only after system/code filter |
| coding system | `{ "path": "system", "name": "code_system" }` | `Coding.system` string | Exact chartevents URI on 9,791/9,791 target rows |
| `d_items.label` (not output) | `{ "path": "display", "name": "code_display" }` | `Coding.display` string | 9,791/9,791 populated; source/dimension display agreement 9,791/9,791 |
| `valuenum` → component values | `{ "path": "(value).ofType(Quantity).value", "name": "quantity_value" }` | `Quantity.value` decimal; materialized alias `STRING` | 9,791/9,791 populated; cast to `FLOAT` for component pivots |
| `valueuom` (not selected by source SQL) | `{ "path": "(value).ofType(Quantity).unit", "name": "quantity_unit" }` | `Quantity.unit` string | 0/9,791 populated, matching source `valueuom` NULL on 9,791/9,791 |
| source text if FHIR string | `{ "path": "(value).ofType(string)", "name": "value_string" }` | `value[x]` `string` | 0/9,791 populated; it does not carry `No Response-ETT` |
| resource identity (support only) | `{ "path": "getResourceKey()", "name": "observation_key" }` | opaque resource key string | 9,791/9,791 populated/distinct; never output or decode it |

The Observation schema also exposes `effectiveInstant` and `effectivePeriod`.
For the GCS target, `effectiveInstant` and Period start/end were each 0/9,791;
only `effective.dateTime` exists, so no effective-choice COALESCE is required.

The canonical output natural key is **`(stay_id, charttime)`**, from the oracle
manifest (`keyed_join`, 1,637,763 rows), not the resource UUID and not `itemid`.
The implementer must pivot at `(stay_id, charttime)` and must not output
`itemid`, `rn`, or `observation_key`.

## Exact coded filter and source-value confirmation

The source SQL names exactly `223900`, `223901`, and `220739`; no terminology
translation or expansion is used. DuckDB source counts:

| `itemid` | total rows | `value` non-null | `value` NULL | `valuenum` non-null | `valueuom` non-null |
|---:|---:|---:|---:|---:|---:|
| 220739 | 3,274 | 3,274 | 0 | 3,274 | 0 |
| 223900 | 3,266 | 3,266 | 0 | 3,266 | 0 |
| 223901 | 3,251 | 3,251 | 0 | 3,251 | 0 |

The source has 9,791 rows and 3,279 distinct `(stay_id, charttime)` groups.
It has zero repeated `(stay_id, charttime, itemid)` groups in the demo. The
served FHIR-to-source join on `(stay_id, charttime, itemid)` matched **9,791 /
9,791** rows, with numeric Quantity agreement within `1e-6` on **9,791/9,791**.

The exact source sentinel is `itemid=223900 AND value='No Response-ETT'`:

* `No Response-ETT`: 1,348 rows, all with `valuenum=1`;
* `No Response`: 78 rows, all with `valuenum=1`;
* all 3,266 verbal rows have non-NULL `valuenum`;
* served verbal Quantity value `1`: 1,426 rows; served `valueString`: 0/3,266.

Thus Quantity `1` cannot discriminate the sentinel, and the exact label has no
direct FHIR path. The ETL branch at
`mimic-fhir/sql/fhir_observation_chartevents.sql:69-80` emits Quantity whenever
`valuenum` is non-NULL and only emits `valueString` when `valuenum` is NULL.

## GCS derivation and representation loss

`gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, and `gcs_unable` are not direct
FHIR elements; they must be derived from the mapped rows using the source
analyst's exact grouping, `MAX` pivots, immediate-previous-row six-hour join,
defaults (6, 5, 4), and ETT branch (total 15 and verbal sentinel 0/flag 1).

The `No Response-ETT` discriminator is **absent and not representable through
FHIR semantics**: both it and `No Response` are served as Quantity 1, and no
other Observation element serializes the source text. A Quantity-1 heuristic
has measured accuracy 1,348/1,426 = **94.53%** for sentinel identification and
false-positive rate 78/1,426 = **5.47%**; it is not exact and must not be used.
The source value is not reconstructable from resource/reference identity; the
identity side channel is expressly forbidden above.

This loss is **essential**, not ancillary. It changes row-level `gcs_unable`,
`gcs_verbal`, total `gcs`, and the six-hour carry-forward branch. A value of 1
can represent two source states with different outputs. It can therefore alter
clinically meaningful derived values and downstream `first_day_gcs`, `sofa`,
and `sapsii`; recommend whole-concept blocking to the equivalence judge rather
than emitting an estimate or only a NULL flag. The prober does not make the
terminal decision.

There is a second, non-label loss: the ETL drops selected source rows whose
`value` is NULL (`fhir_observation_chartevents.sql:34-38`), while the canonical
GCS WHERE clause filters only itemid. It is not exercised by the demo target
(0/9,791 source `value` NULL), but may produce `only_oracle` rows on full data.
This is a coverage gap; do not invent rows or values. The ETL's hard-coded
duplicate exclusion was also absent from the demo GCS source target.

Served `effectiveDateTime` is the only charttime mapping. Parse it as a MIMIC
wall clock with `TIMESTAMP_NTZ`; do not use an offset-aware cast and do not use
Observation.id to undo upstream DST-gap normalisation. Such a normalisation is
an upstream representational transform to be classified by the comparator and
judge, not recoverable through this mapping.

## Notes read and findings

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the canonical
`v_observation.viewdefinition.json`, the source analysis, ETL SQL, and all
fragments in `MIMIC_NOTES.d/` (including `gcs.md`, `crrt.md`, and
`code_status.md`; also `README.md`, `cardiac_marker.md`, `chemistry.md`,
`coagulation.md`, `complete_blood_count.md`, `blood_differential.md`,
`dobutamine.md`, `dopamine.md`, `epinephrine.md`, `icustay_detail.md`,
`invasive_line.md`, `arb.md`, `kdigo_creatinine.md`, `icp.md`, and the other
present fragments). All fragment claims were treated as provisional leads and
were independently checked where relevant; irrelevant medication/lab claims
were not promoted.

Established `MIMIC_NOTES.md` entries that changed this mapping decision:

* Delta, not stale NDJSON/server, is authoritative.
* System plus exact code, never `meta.profile`, discriminates Observation
  streams; code is the verbatim itemid.
* Identifier values are strings; subject/stay outputs require identifier joins
  and final integer casts, while reference/resource UUIDs are opaque.
* FHIR dateTimes require `TIMESTAMP_NTZ` wall-clock parsing.
* Categorical chartevents use `valueString`; this GCS probe confirmed this
  numeric target instead uses Quantity and has no string sentinel path.
* Essential source loss blocks a whole derived concept; typed NULL is not a
  remedy for a discriminator that changes core derivation.

The provisional `gcs.md` NULL-omission and numeric-text-loss entries were
verified against the ETL and the GCS counts. The `crrt.md` repeated-row/DST
leads and `code_status.md` omission/DST leads were read but not adopted without
GCS-specific checks. Their historical UUID-recovery recommendations were
explicitly rejected as forbidden by the opaque-identity rule.

No new dataset-wide quirk was found that is absent from `MIMIC_NOTES.md` or the
owned `gcs.md` fragment, so **nothing was appended** to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/gcs.md` in this rerun. No ViewDefinition,
concept SQL, or attempt artifact was created.
