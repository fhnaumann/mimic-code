# FHIR mapping: `first_day_urine_output`

## Scope and probe sources

- Source analysis: `mimic-iv/concepts_fhir/carryover/first_day_urine_output/source-analyst.md`.
- Canonical source SQL: `mimic-iv/concepts/firstday/first_day_urine_output.sql`.
- Authoritative warehouse probed with embedded Pathling 9.6.0/Spark 4.0.2:
  `/Users/nau025/warehouses/mimic-iv-demo/delta`.
- Read-only DuckDB oracle used for source counts and agreement checks:
  `/Users/nau025/warehouses/mimic4-demo.db`.
- ETL checked: `/Users/nau025/Documents/mimic-fhir/sql/fhir_encounter_icu.sql` and
  `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_outputevents.sql`.
- Structural reference checked:
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- All probe queries used equality on Pathling resource/reference keys. No
  `Resource.id` was parsed, no key was regenerated, and no key was used to
  infer a source timestamp or identifier.

## Resource/table mapping

| MIMIC source | FHIR resource or published dependency | Mapping |
|---|---|---|
| `mimiciv_icu.icustays` | ICU `Encounter` resources | One ICU Encounter per stay; select the ICU stream with `Encounter.identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`. `Encounter.class` is not used. |
| `icustays.subject_id` | `Encounter.subject` → `Patient.identifier` | Join the Encounter's `subject.getReferenceKey(Patient)` to `Patient.getResourceKey()` and read the patient identifier system. The identifier value is a FHIR `string`, then the final SQL casts it to manifest `INTEGER`. |
| `icustays.stay_id` | `Encounter.identifier` | Read `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value`; it is a FHIR `string`, then cast to final `INTEGER`. Do not use `Encounter.getResourceKey()` as `stay_id`. |
| `icustays.intime` | `Encounter.period.start` | FHIR `dateTime`; the materialized Pathling alias is `string` and must be `CAST(... AS TIMESTAMP_NTZ)` for the inclusive window. |
| completed `mimiciv_derived.urine_output` view | Published dependency `urine_output` | The implementer must use `FROM urine_output`; it must not read `Observation`/`outputevents` or inline/rederive the dependency's item/value transformation. The published dependency supplies `charttime`, `urineoutput`, `icu_encounter_key`, and `patient_key`. |
| dependency `uo.charttime` | dependency upstream `Observation.effective[x]` | The upstream outputevents Observation uses the dateTime variant only. The dependency materializes `CAST(effective_datetime AS TIMESTAMP_NTZ)` as `charttime`; the target only consumes this dependency column for the window predicate. |
| dependency `uo.urineoutput` | dependency upstream `Observation.value.ofType(Quantity).value` plus code | The completed dependency has already applied the `227488 AND value > 0` negation and grouped by stay/time. The target only sums the published `uo.urineoutput`; it must not repeat this CASE. |

## Canonical FHIRPath projections

These are the projections needed by the target and its completed dependency.
The Observation projection is documented as upstream dependency mapping only;
it is not permission to inline `urine_output` in this concept.

### ICU Encounter view

```json
{
  "resource": "Encounter",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "icu_encounter_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
      {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"},
      {"path": "period.start", "name": "intime_datetime"}
    ]}
  ]
}
```

### Patient view

```json
{
  "resource": "Patient",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "patient_key"},
      {"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}
    ]}
  ]
}
```

### Upstream outputevents Observation view used by the completed dependency

```json
{
  "resource": "Observation",
  "select": [
    {"column": [
      {"path": "getResourceKey()", "name": "observation_key"},
      {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
      {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"},
      {"path": "(value).ofType(Quantity).value", "name": "value_quantity"},
      {"path": "(value).ofType(Quantity).unit", "name": "value_unit"},
      {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
      {"path": "(effective).ofType(Period).start", "name": "effective_period_start"},
      {"path": "(effective).ofType(Period).end", "name": "effective_period_end"},
      {"path": "(effective).ofType(instant)", "name": "effective_instant"}
    ]},
    {"forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items' and (code='226559' or code='226560' or code='226561' or code='226584' or code='226563' or code='226564' or code='226565' or code='226567' or code='226557' or code='226558' or code='227488' or code='227489'))", "column": [
      {"path": "code", "name": "item_code"},
      {"path": "system", "name": "item_system"},
      {"path": "display", "name": "display"}
    ]}
  ]
}
```

## Source-column → FHIRPath mapping and target types

FHIR identifier values and ViewDefinition aliases are strings. The final
concept SQL must cast the two numeric identifiers, while resource keys remain
uncast, type-prefixed opaque strings.

| Source column / derived input | Canonical mapping `{path, name}` | FHIR type | Pathling materialized type | Required target type/use |
|---|---|---|---|---|
| `ie.subject_id` | Patient `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` reached through Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | `Identifier.value` `string`; `Reference(Patient)` key | `StringType` | `CAST(subject_id_str AS INTEGER)` as `subject_id`; emit `patient_key` verbatim |
| `ie.stay_id` | ICU Encounter `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` | `Identifier.value` `string` | `StringType` | `CAST(stay_id_str AS INTEGER)` as `stay_id`; emit `icu_encounter_key` alongside it |
| ICU stay resource identity | ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}` | resource key / opaque identity string | `StringType` | Required output key, uncast and type-prefixed; equality joins only |
| Patient resource identity | Encounter `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` or Patient `{path: "getResourceKey()", name: "patient_key"}` | reference/resource key string | `StringType` | Required output key, uncast and type-prefixed; equality joins only |
| `ie.intime` | ICU Encounter `{path: "period.start", name: "intime_datetime"}` | `dateTime` | `StringType` in the probe | `CAST(intime_datetime AS TIMESTAMP_NTZ)` for both inclusive predicates |
| upstream `oe.stay_id` / source dependency `uo.stay_id` | Observation `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` joined to ICU Encounter `{path: "getResourceKey()", name: "icu_encounter_key"}`, then the ICU identifier path above | `Reference(Encounter)` plus `Identifier.value` `string` | keys and identifier are `StringType` | In the completed published dependency, `stay_id` is stripped when paired with `icu_encounter_key`; join `e.icu_encounter_key = uo.icu_encounter_key`, recover/output `stay_id` from the ICU Encounter identifier. Never join a published dependency on a dropped `uo.stay_id`. |
| `uo.charttime` | Upstream Observation `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` | `StringType` | Already published as dependency `charttime`; consume it and compare with `CAST(intime_datetime AS TIMESTAMP_NTZ)` |
| `oe.itemid` (dependency-only discriminator) | Within the constrained `forEach`: `{path: "code", name: "item_code"}` plus `{path: "system", name: "item_system"}` | `Coding.code/system` `string` | `StringType` | Exact system + code filter upstream; `CAST(item_code AS INTEGER)` only inside dependency implementation |
| `oe.value` (dependency-only numeric input) | `{path: "(value).ofType(Quantity).value", name: "value_quantity"}` | `Quantity.value` decimal | `StringType` for the ViewDefinition alias | `CAST(value_quantity AS DOUBLE)` upstream; target consumes published `uo.urineoutput` |
| `oe.valueuom` (not used by target SQL) | `{path: "(value).ofType(Quantity).unit", name: "value_unit"}` | `Quantity.unit` `string` | `StringType` | Available upstream (`ml` on all 7,349 target rows), not an output column |
| `uo.urineoutput` | No single final FHIRPath; completed dependency's grouped value | numeric aggregate | published dependency `DOUBLE` | `SUM(uo.urineoutput)` as final `DOUBLE`; no rederivation |
| final `urineoutput` | No single FHIR element; target aggregation | `DOUBLE` | n/a | `DOUBLE` |

## Dependency boundary and joins

The source SQL says `ie.stay_id = uo.stay_id`, but a dependency is consumed in
its published resource-key shape. The completed `urine_output` attempt's
published projection, verified with `strip_mimic_ids`, drops `stay_id` because
it is paired with `icu_encounter_key`; it supplies:

```text
charttime, urineoutput, icu_encounter_key, patient_key
```

Therefore the target implementation must use the semantically equivalent,
opaque equality join:

```sql
FROM icu_encounter e
LEFT JOIN urine_output uo
  ON e.icu_encounter_key = uo.icu_encounter_key
 AND uo.charttime >= e.intime_datetime
 AND uo.charttime <= e.intime_datetime + INTERVAL 1 DAY
```

The source's stay equality is preserved by the one-to-one ICU Encounter key /
identifier relationship, without parsing or regenerating a key. The left join
and both inclusive boundaries must remain in `ON`; every ICU stay is retained,
and an entirely unmatched `SUM` remains SQL `NULL` (no `COALESCE`). Group by
the ICU Encounter/stay grain and emit `subject_id`, `stay_id`, `urineoutput`,
`patient_key`, and `icu_encounter_key`. Keys for unmatched stays come from the
ICU Encounter side, not the nullable dependency side.

The target has no direct code filter. The exact code filter belongs only to the
completed `urine_output` dependency and must not be copied into this concept.

## Confirmed code system, literals, and cardinality

The served Delta carried the exact upstream system:

```text
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items
```

The source SQL's twelve literals were checked against both the DuckDB source
and the system/code-constrained Pathling projection:

| Itemid | Source rows | FHIR rows/resources | `d_items.linksto` |
|---:|---:|---:|---|
| 226559 | 6,685 | 6,685 / 6,685 | outputevents |
| 226560 | 496 | 496 / 496 | outputevents |
| 226561 | 90 | 90 / 90 | outputevents |
| 226584 | 0 | 0 / 0 | outputevents |
| 226563 | 0 | 0 / 0 | outputevents |
| 226564 | 0 | 0 / 0 | outputevents |
| 226565 | 0 | 0 / 0 | outputevents |
| 226567 | 15 | 15 / 15 | outputevents |
| 226557 | 0 | 0 / 0 | outputevents |
| 226558 | 0 | 0 / 0 | outputevents |
| 227488 | 32 | 32 / 32 | outputevents |
| 227489 | 31 | 31 / 31 | outputevents |
| **total** | **7,349** | **7,349 / 7,349** | |

The zero counts are demo-cohort zeroes; all twelve literals remain in the
dependency specification. `outputevents` and `datetimeevents` share the
`mimic-d-items` system, but the twelve `d_items.itemid` rows are a global PK,
each has exactly one `linksto='outputevents'`, and the demo source had zero
outputevents/datetimeevents itemid overlap. Thus `system + exact code` is the
discriminator. Do not use `meta.profile`.

For the unconstrained `mimic-d-items` coding projection, coding rows/resources
were 24,642 / 24,642 (ratio 1.000). For the exact urine subset they were
7,349 / 7,349 (ratio 1.000), so the constrained `forEach` has no fan-out.

## Populated-field and oracle checks

On the exact 7,349-row urine subset, the Pathling projection counted:

- `observation_key`: 7,349/7,349;
- `patient_key`: 7,349/7,349;
- `encounter_key`: 7,349/7,349;
- `value_quantity`: 7,349/7,349;
- `value_unit`: 7,349/7,349 (`ml` on all rows);
- `effective_datetime`: 7,349/7,349;
- `effective_period_start`: 0/7,349;
- `effective_period_end`: 0/7,349;
- `effective_instant`: 0/7,349.

Encounter/identifier probes found 637 total Encounter resources with 140 ICU
identifiers, 275 hospital identifiers, and 222 ED identifiers. All identifier
values were `string`. Patient had 100/100 patient-system identifier values,
also `string`. The ICU Encounter projection joined to its Patient projection
by opaque key and agreed with the source oracle on 140/140 `stay_id` values,
140/140 `subject_id` values, and 140/140 `intime` values. The Observation
encounter-key join resolved all 7,349/7,349 outputevents rows to an ICU stay.

Read-only source/FHIR checks were exact on the demo: outputevent keys 7,349/7,349,
Quantity values 7,349/7,349, units 7,349/7,349, and first-day aggregate rows
140/140 with `subject_id` exact 140/140 and `urineoutput` exact (or both NULL)
140/140. The FHIR replay retained 7,349 event rows and 7,317 grouped
`(stay_id, charttime)` rows. The final target manifest requires:

```text
subject_id INTEGER
stay_id INTEGER                 -- comparison key
urineoutput DOUBLE
patient_key                     -- required opaque key column
icu_encounter_key               -- required opaque key column
```

## Gaps and representability

1. **Outputevents DST-gap wall time — absent and not recoverable from FHIR.**
   The ETL casts `outputevents.charttime` through `TIMESTAMPTZ` before writing
   `Observation.effectiveDateTime` (`fhir_observation_outputevents.sql:9,60`).
   A spring-forward 02:xx wall time can therefore be stored as 03:xx; the
   original wall value is not present in another FHIR element. The target's
   `charttime` controls the dependency grouping key and both inclusive
   first-day predicates, so this loss is potentially essential: it can alter
   row inclusion, grouping, and the clinically meaningful sum. The demo bound
   was 0/7,349 changed event keys and 0/140 aggregate divergences (although
   334 demo target source events were in the 02:xx hour); the full affected
   count is not available in this local warehouse. Use `TIMESTAMP_NTZ` to
   preserve the served wall value and never repair it through a resource id.
   Under the generic essential-loss rule, an unresolved loss reaching these
   rows would warrant a whole-concept blocking recommendation. Here the loss
   is the specifically documented upstream TIMESTAMPTZ transformation, so the
   shared policy routes it to equivalence-judge review rather than allowing a
   prober-side block; it is not a reason to invent a key or inline the
   dependency.

2. **No other target-essential gap found.** `subject_id`, `stay_id`, `intime`,
   outputevent code, Quantity value, ICU Encounter references, and Patient
   references all had exact demo source mappings. `storetime`, `valueuom`, and
   individual Observation identity are not consumed by the target SQL. The
   Observation/resource keys are opaque equality identities only.

## Notes and provisional fragments

`MIMIC_NOTES.md` entries that changed mapping decisions were the identifier
spine (identifier values are strings and must be cast while keys are required
outputs), type-prefixed opaque resource/reference keys, the itemid-verbatim
Observation coding rule and system+code discriminator, the `outputevents` /
`datetimeevents` shared coding-system warning, the `TIMESTAMP_NTZ` datetime
rule, and the prohibition on using ids as a semantic side channel.

Read fragments: `MIMIC_NOTES.d/urine_output.md`,
`MIMIC_NOTES.d/first_day_bg.md`, `MIMIC_NOTES.d/rrt.md`, and
`MIMIC_NOTES.d/icustay_times.md`, plus the source carryover for this concept.
The urine-output dateTime lead was independently verified above. Its DST/full-
run claim was treated as provisional: this probe independently verified the
ETL mechanism and demo impact bound, but did not rerun the full HPC comparison.
The first-day-bg, RRT, and icustay-times fragments concern labevents,
chartevents, or other aggregates and did not change this outputevents mapping;
they were read but not adopted as evidence for this concept.

This run appended the two dataset/IG-wide findings confirmed by the probe to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_urine_output.md`: outputevents
effective timing is dateTime-only, and its upstream TIMESTAMPTZ normalization
can affect first-day aggregation. No other fragment or `MIMIC_NOTES.md` was
edited.
