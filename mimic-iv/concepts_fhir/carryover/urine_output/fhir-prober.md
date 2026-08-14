# FHIR mapping: `urine_output`

## Scope and authoritative sources

- Source analysis: `mimic-iv/concepts_fhir/carryover/urine_output/source-analyst.md`.
- Canonical source table: `mimiciv_icu.outputevents`.
- FHIR warehouse probed with embedded Pathling 9.6.0/Spark 4.0.2 over
  `/Users/nau025/warehouses/mimic-iv-demo/delta`.
- Local ETL checked: `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_outputevents.sql`.
- Source oracle checked read-only at `/Users/nau025/warehouses/mimic4-demo.db`.

## Source table to FHIR resource mapping

| Source | FHIR resource/element | Finding |
|---|---|---|
| `mimiciv_icu.outputevents` | `Observation` | The outputevents ETL creates one outputevents Observation stream. Use `Observation.code.coding.system` plus the exact item code, not `meta.profile`, as the discriminator. |
| `outputevents.stay_id` | `Observation.encounter` → ICU `Encounter` | The Observation reference joins by opaque `encounter.getReferenceKey(Encounter)`. Resolve that key against an ICU Encounter ViewDefinition and read its ICU identifier value. |
| ICU stay identity used for the join | `Encounter.identifier` | Filter `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`; the value is the source `stay_id` as a FHIR string. Do not use `getResourceKey()` or parse any UUID. |

The authoritative demo had 637 Encounters: 140 ICU, 275 hospital, and 222 ED.
All 7,349 urine-output Observations joined to a non-null ICU `stay_id` value
(7,349/7,349); the ICU Encounter identifier projection had 140/140 values.

## Canonical ViewDefinition projections

These are the required `select[].column[]` mappings. The aliases ending in
`_key` are opaque UUID/reference strings for equality joins only. The aliases
ending in `_str` are FHIR `string` values and must be cast in the final SQL.

### Observation view

```json
{
  "resource": "Observation",
  "select": [
    {
      "column": [
        {"path": "getResourceKey()", "name": "observation_key"},
        {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
        {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"},
        {"path": "(value).ofType(Quantity).value", "name": "value_quantity"},
        {"path": "(value).ofType(Quantity).unit", "name": "value_unit"},
        {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
        {"path": "(effective).ofType(Period).start", "name": "effective_period_start"},
        {"path": "(effective).ofType(Period).end", "name": "effective_period_end"},
        {"path": "(effective).ofType(instant)", "name": "effective_instant"}
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items')",
      "column": [
        {"path": "code", "name": "code"},
        {"path": "system", "name": "system"},
        {"path": "display", "name": "display"}
      ]
    }
  ]
}
```

Filter `code` to the twelve exact literals below in SQL after the system-
constrained coding projection, or constrain the same exact code set inside
the `forEach` if the runner's FHIRPath parser accepts that expression.

### ICU Encounter view used to recover `stay_id`

```json
{
  "resource": "Encounter",
  "select": [
    {
      "column": [
        {"path": "getResourceKey()", "name": "encounter_key"},
        {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"}
      ]
    }
  ]
}
```

The Observation-to-Encounter join is `observation.encounter_key =
encounter.encounter_key`, followed by `CAST(stay_id_str AS INTEGER)` in the
outer query. `getReferenceKey(Encounter)`/`getResourceKey()` are not source
identifiers and must never be emitted as `stay_id`.

## Source-column mapping and target types

| Source input | Canonical FHIRPath mapping `{path, name}` | FHIR type | Pathling materialized type | Required final SQL type / use |
|---|---|---|---|---|
| `oe.stay_id` (`INTEGER`) | Observation `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}`; ICU Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | `Reference(Encounter)` plus `Identifier.value` `string` | `VARCHAR` for both aliases | Join on opaque `encounter_key`; `CAST(stay_id_str AS INTEGER)` as output `stay_id` and grouping input |
| `oe.charttime` (`TIMESTAMP(3)`) | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` | `VARCHAR` (ISO-8601 string with offset) | `CAST(effective_datetime AS TIMESTAMP_NTZ)` as output `charttime`; this preserves the MIMIC wall-clock value |
| `oe.itemid` (`INTEGER`) | Within system-constrained `forEach`: `{path: "code", name: "code"}` and `{path: "system", name: "system"}`; optional `{path: "display", name: "display"}` | `Coding.code/system/display` `string` | `VARCHAR` | Filter exact `system` and exact string code first, then `CAST(code AS INTEGER)` as `itemid`; display is not a discriminator |
| `oe.value` (`FLOAT`) | `{path: "(value).ofType(Quantity).value", name: "value_quantity"}` | `Quantity.value` decimal | `VARCHAR` for the ViewDefinition alias; raw `valueQuantity.value` is `decimal(32,6)` | `CAST(value_quantity AS DOUBLE)`; apply the `227488 AND value > 0` negation before `SUM` |
| `oe.valueuom` (`VARCHAR`, not referenced by canonical SQL) | `{path: "(value).ofType(Quantity).unit", name: "value_unit"}` | `Quantity.unit` `string` | `VARCHAR` | Not needed by this concept. All 7,349 target rows had `ml`. |
| Per-row `urineoutput` | No single FHIR element; derived from `itemid` and Quantity value | numeric expression | n/a | `CASE WHEN itemid=227488 AND value > 0 THEN -value ELSE value END` |
| Final `SUM(urineoutput)` | No single FHIR element; grouping operation | `DOUBLE` output | n/a | Group by recovered `stay_id` and `charttime`; preserve every Observation row before aggregation |

`observation_key` and `patient_key` are useful only for resource identity and
joins/provenance. The source query does not output either. The outputevents ETL
also writes `Observation.issued` from `storetime`, but `storetime` is not a
source input to `urine_output` and is not required in this view.

## Confirmed coding system and exact code set

The served Delta, not a terminology lookup, established the coding system as:

`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`

The source SQL's exact twelve itemids were counted in the DuckDB source and in
the system/code-filtered Observation projection. Counts agreed for every code:

| Itemid | Source rows | FHIR rows/resources | Source display |
|---:|---:|---:|---|
| 226559 | 6,685 | 6,685 / 6,685 | Foley |
| 226560 | 496 | 496 / 496 | Void |
| 226561 | 90 | 90 / 90 | Condom Cath |
| 226584 | 0 | 0 / 0 | Ileoconduit |
| 226563 | 0 | 0 / 0 | Suprapubic |
| 226564 | 0 | 0 / 0 | R Nephrostomy |
| 226565 | 0 | 0 / 0 | L Nephrostomy |
| 226567 | 15 | 15 / 15 | Straight Cath |
| 226557 | 0 | 0 / 0 | R Ureteral Stent |
| 226558 | 0 | 0 / 0 | L Ureteral Stent |
| 227488 | 32 | 32 / 32 | GU Irrigant Volume In |
| 227489 | 31 | 31 / 31 | GU Irrigant/Urine Volume Out |
| **total** | **7,349** | **7,349 / 7,349** | |

The zeroes are demo-cohort zeroes, not permission to remove those literals
from the full-data filter. `d_items` has one row and `linksto='outputevents'`
for each of the twelve itemids; no itemid has multiple `linksto` values. The
demo has zero itemid overlap between `outputevents` and `datetimeevents`.
Thus `system + exact code` separates this source stream even though both
streams use the same `mimic-d-items` system. Never use `meta.profile`.

## Coding cardinality and populated-field counts

An unfiltered projection of the served `mimic-d-items` system had 24,642
coding rows for 24,642 distinct Observation resource keys: ratio **1.000**.
The system-constrained `forEach` produced zero fan-out. The urine-output exact
code subset had 7,349 rows for 7,349 distinct resources: ratio **1.000**.

For the exact subset (rows total → non-null):

- `encounter_key`: 7,349 → 7,349.
- ICU `stay_id_str` after the reference join: 7,349 → 7,349.
- `value_quantity`: 7,349 → 7,349; numeric cast succeeded on 7,349.
- `value_unit`: 7,349 → 7,349 (`ml` on all rows).
- `effective_datetime`: 7,349 → 7,349.
- `effective_period_start`: 7,349 → 0.
- `effective_period_end`: 7,349 → 0.
- `effective_instant`: 7,349 → 0.

The encoded effective-time aliases had these materialized types: dateTime and
Period start/end were `string`; instant was native Spark `timestamp`. The
outputevents ETL writes only `effectiveDateTime` (not a Period or instant), so
project the dateTime variant and retain the other variants as typed diagnostic
columns only if the shared view is reused.

## Aggregation/cardinality confirmation

The source target subset had 7,349 rows and 7,317 distinct `(stay_id,
charttime)` groups. There were 32 duplicate stay/time groups, all caused by
different itemids; each itemid individually had no duplicate `(stay_id,
charttime)` pair, and the maximum target group size was 2. The FHIR target
projection retained all 7,349 rows and the same 7,317 groups. Do not
deduplicate by Observation id, stay/time, or item code before applying the
CASE and sum.

The `227488` branch had 32/32 positive values in the demo, so the source
transformation is computable from the surviving code and Quantity value. The
source raw sum was `77125.0`; the transformed sum was `-77125.0`.

Read-only DuckDB-to-FHIR comparison after resolving the ICU Encounter
identifier found:

- raw tuple alignment on `(stay_id, charttime, itemid)`: **7,349/7,349** rows;
- raw source value versus FHIR Quantity value: **7,349/7,349 exact**;
- grouped `(stay_id, charttime)` rows: **7,317/7,317** aligned;
- grouped `SUM(CASE...)` urineoutput: **7,317/7,317 exact**.

## Effective-time and ETL-loss assessment

`fhir_observation_outputevents.sql:9,60` casts source `charttime` through
`TIMESTAMPTZ` before writing `Observation.effectiveDateTime`. The served
effective value carries an offset, so the final SQL must use
`CAST(effective_datetime AS TIMESTAMP_NTZ)`, not an offset-aware cast to Spark
`TIMESTAMP`. In this authoritative demo, all 7,349 target charttimes agreed
exactly after the NTZ cast, so the measured loss is **0/7,349** target rows.

The shared datetime note establishes that the upstream `TIMESTAMPTZ` cast can
irreversibly normalize a nonexistent New York spring-forward 02:xx wall time
to 03:xx. That original wall time is not recoverable from
`Observation.effectiveDateTime`, and the resource id is not a permitted side
channel. For this concept such a loss is potentially essential: `charttime` is
part of the output natural key and the `GROUP BY`, so a shifted time can split,
merge, or change a summed row. No affected row was observed in the demo; the
full-data comparator must bound the full cohort's affected rows. If the full
run finds DST-gap rows/collisions, they are not an ancillary typed-NULL field
gap and should be presented to the equivalence judge as a whole-concept
representability issue rather than repaired through id parsing.

The ETL constructs `Observation.id` from a UUID involving
`stay_id-charttime-itemid`, but this is opaque FHIR identity. Do not regenerate,
parse, brute-force, hardcode, or compare candidate UUIDs to guessed source
values. The source row identifier is not otherwise serialized; this does not
prevent the concept's representable `(stay_id, charttime)` aggregation grain
in the ordinary (non-normalized) case.

## Probe commands/evidence

The evidence was produced by embedded Pathling/Spark probes over the Delta and
read-only DuckDB queries over the demo oracle:

1. `src.read('Observation').schema` confirmed the Observation choice fields,
   raw `valueQuantity.value decimal(32,6)`, `effectiveDateTime string`,
   `effectiveInstant timestamp`, and `effectivePeriod` struct.
2. A system-constrained `forEach` ViewDefinition projection counted 24,642
   rows/resources (ratio 1.000), and the exact code projection counted 7,349
   rows/resources (ratio 1.000).
3. The exact-code counts, field non-null counts, effective variants, and
   Observation-to-ICU-Encounter join were counted in Spark.
4. DuckDB counted source itemids, `d_items.linksto`, item overlap with
   `datetimeevents`, source duplicates, and the `227488` CASE population.
5. A pandas comparison of resolved FHIR rows against DuckDB and a grouped
   aggregate comparison established the exact rates reported above.

The relevant ETL lines are `mimic-fhir/sql/fhir_observation_outputevents.sql:8-19`
(source values/references/id), `:51-68` (code/value/effective/issued), and
`mimic-fhir/sql/codesystem/vs-outputevents-d-items.sql:12-17` (system and
dimension display).
