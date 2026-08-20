# FHIR mapping: `first_day_rrt`

## Authority and probe basis

The source specification is `mimic-iv/concepts/firstday/first_day_rrt.sql`,
and the source analysis is
`mimic-iv/concepts_fhir/carryover/first_day_rrt/source-analyst.md`.  The
authoritative served-data probes used embedded Pathling 9.6.0 on Spark 4.0.2
over:

```text
/Users/nau025/warehouses/mimic-iv-demo/delta
```

The read-only demo oracle used for source checks was
`/Users/nau025/warehouses/mimic4-demo.db`.  The ViewDefinition structure was
checked against
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
Raw `Mimic*.ndjson.gz` files and the live Pathling server were not used.

The target manifest entry is:

```text
columns: subject_id INTEGER, stay_id INTEGER,
         dialysis_present INTEGER, dialysis_active INTEGER,
         dialysis_type VARCHAR
comparison: keyed_join
key: stay_id
required key columns: icu_encounter_key, patient_key
demo oracle rows: 140
```

The required key columns are emitted in addition to the five compared
columns.  They are opaque FHIR identity strings and must be retained verbatim.

## Mapping decisions from the established notes

The following `MIMIC_NOTES.md` entries changed this mapping:

- **MIMIC ids live in `identifier.value` as STRINGs**: `subject_id` and
  `stay_id` come from filtered identifier values, not resource keys, and the
  final SQL must cast them to `INTEGER`.
- **`getResourceKey()` is type-prefixed and opaque**: `Encounter/<uuid>` and
  `Patient/<uuid>` are equality-join keys only; they must not be parsed,
  regenerated, or used to recover source values.
- **Encounter has three identifier systems; class discriminates none**: the
  ICU population is selected with
  `identifier.system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`,
  never with `Encounter.class`.
- **FHIR datetimes carry offsets**: the FHIR `period.start` string must be
  converted with `TRY_CAST(... AS TIMESTAMP_NTZ)`, not an offset-aware parser
  that converts through the local timezone.
- **DST-gap timestamps are irreversibly shifted**: do not try to repair an
  upstream FHIR time with a resource id.  The target's `intime` is a temporal
  inclusion input, so any full-data residual from the established upstream
  cast must be bounded and reported to the judge.

The dependency boundary also follows the identifier-spine and derived-table
rules in the `fhir-mapping` skill and `AGENTS.md`: join on resource keys, not
on integer identifiers, and consume the already-preprocessed `rrt` temp view.

## Resource/table mapping

| Source role | Served resource/relation | Mapping and evidence |
|---|---|---|
| `mimiciv_icu.icustays` ICU-stay population | `Encounter`, ICU stream | Filter the unfiltered Encounter table by the ICU identifier system. The Delta has 637 Encounters: 275 hosp, 222 ED, 140 ICU. The filtered ICU view has 140 rows, 140 distinct resource keys, and 140 distinct stay identifiers. |
| `mimiciv_icu.icustays.subject_id` | `Patient` through `Encounter.subject` | ICU Encounter `subject.getReferenceKey(Patient)` joins to `Patient.getResourceKey()`. The Patient identifier system carries the source subject id as a string. The demo join to the source oracle is 140/140 exact. |
| `mimiciv_icu.icustays.intime` | ICU `Encounter.period.start` | FHIR `dateTime`, materialized by Pathling as a string. `TRY_CAST(period_start AS TIMESTAMP_NTZ)` agrees with `icustays.intime` for 140/140 demo stays. |
| completed `mimiciv_derived.rrt` dependency | preprocessed Spark temp view `rrt` | Do not read raw FHIR or inline `rrt.sql`. The embedded executor runs the completed `rrt` attempt first, applies the published-shape identifier strip, and registers the result as `rrt`. |

The completed dependency is `rrt` attempt 0004, whose state is
`COMPLETED_WITH_DIVERGENCE`.  Its accepted upstream DST behavior is inherited
at this boundary; `first_day_rrt` must not attempt a second RRT derivation or
repair it with resource ids.

## Canonical ViewDefinition projections

These are mapping specifications for the implementer.  Keep the `_str` and
`_key` aliases in the FHIR views and cast only in the final SQL.

### ICU Encounter view

Resource: `Encounter`.  The identifier filter is essential: the unfiltered
Encounter view contains hosp and ED encounters as well as ICU stays.

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "name": "first_day_rrt_encounter",
  "resource": "Encounter",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "icu_encounter_key" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
        { "path": "period.start", "name": "period_start" },
        { "path": "period.end", "name": "period_end" }
      ]
    },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu')",
      "column": [
        { "path": "value", "name": "stay_id_str" }
      ]
    }
  ]
}
```

The probe materialized this view as:

```text
icu_encounter_key string   140/140 non-null, 140 distinct
patient_key       string   140/140 non-null
period_start      string   140/140 non-null
period_end        string   140/140 non-null
stay_id_str       string   140/140 non-null, 140 distinct
```

`period_end` is included to document the Encounter period but is not consumed
by `first_day_rrt.sql`; the source target uses `intime` only and has no
`outtime` predicate.

### Patient identifier view

Resource: `Patient`.

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "name": "first_day_rrt_patient",
  "resource": "Patient",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "patient_key" }
      ]
    },
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient')",
      "column": [
        { "path": "value", "name": "subject_id_str" }
      ]
    }
  ]
}
```

The Patient probe returned 100 resources, with `patient_key` and
`subject_id_str` populated on 100/100 rows and 100 distinct values of each.

## Source-column to FHIRPath mapping

| Source column/expression | Canonical `{path, name}` | FHIR/served type | Required target type and use |
|---|---|---|---|
| `ie.subject_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }` on the Patient view, reached through `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | `identifier.value` is FHIR `string`; Pathling alias is `string` | `CAST(subject_id_str AS INTEGER) AS subject_id`; 140/140 exact against the source subject ids. |
| `ie.stay_id` | `{ "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str" }` | FHIR `Identifier.value` `string`; Pathling alias is `string` | `CAST(stay_id_str AS INTEGER) AS stay_id`; 140/140 exact and 140 distinct in the demo. |
| ICU Encounter resource identity | `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` | Opaque Pathling `string`, type-prefixed `Encounter/<id>` | Emit uncast as the required `icu_encounter_key`; equality join to `rrt.icu_encounter_key` only. Never parse or regenerate it. |
| ICU Encounter patient reference | `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` | Opaque Pathling `string`, type-prefixed `Patient/<id>` | Emit uncast as required `patient_key`; equality join to the Patient view only. |
| `ie.intime` | `{ "path": "period.start", "name": "period_start" }` | FHIR `dateTime`; materialized ViewDefinition type is `string` | `TRY_CAST(period_start AS TIMESTAMP_NTZ)` for both join bounds. Demo agreement with `icustays.intime`: 140/140. |
| `rrt.stay_id` in source analysis | **Not a published dependency column**. Use published `{ "path": "getResourceKey()", "name": "icu_encounter_key" }` from the dependency's ICU Encounter view and join `rrt.icu_encounter_key = e.icu_encounter_key`. | Opaque `string` identity | Do not join `rrt` to `stay_id`; the preprocessing strip removes `stay_id` because `icu_encounter_key` is emitted. This is an equality-key substitution, not id parsing. |
| `rrt.charttime` | Inherited from the completed dependency boundary; no new FHIR projection in this consumer | Published Spark `timestamp_ntz` | Compare directly to the NTZ-cast `period_start`; do not convert it through a timezone. |
| `rrt.dialysis_present` | Inherited dependency column `dialysis_present` | Published Spark `int` | `MAX(rrt.dialysis_present)` → nullable target `INTEGER`. |
| `rrt.dialysis_active` | Inherited dependency column `dialysis_active` | Published Spark `int` | `MAX(rrt.dialysis_active)` → nullable target `INTEGER`. |
| `rrt.dialysis_type` | Inherited dependency column `dialysis_type` | Published Spark `string` / nullable | `STRING_AGG(DISTINCT ...)` equivalent, sorted and delimited by `', '`, then `CAST(... AS VARCHAR(255))` → nullable target `VARCHAR`. |

## Dependency boundary and published shape

The probe reproduced the executor's dependency preprocessing using the
completed `rrt` attempt 0004.  `strip_mimic_ids('rrt', ...)` dropped exactly
`stay_id` because that attempt also projects `icu_encounter_key`.  The
preprocessed temp view available to the target is:

```text
rrt.charttime           timestamp_ntz   5130/5130 non-null
rrt.dialysis_present    int             5130/5130 non-null
rrt.dialysis_active     int             5130/5130 non-null
rrt.dialysis_type       string          4205/5130 non-null
rrt.icu_encounter_key   string          5130/5130 non-null, 9 distinct
rrt.patient_key         string          5130/5130 non-null
```

The demo DuckDB dependency has 5,134 rows, 4,209 non-null
`dialysis_type` values, and 9 distinct stays.  The completed dependency
candidate has 5,130 rows and 4,205 non-null types; this is the already-accepted
upstream datetime transformation in `rrt`, not a reason to rederive it in the
consumer.  The first-day window contains 235 candidate dependency rows across
6 ICU stays, with zero rows exactly at either boundary in the demo.  The
oracle source join independently contains 235 rows across the same 6 stays.

The target SQL should therefore use the following identity and time join:

```sql
FROM first_day_rrt_encounter e
LEFT JOIN first_day_rrt_patient p
  ON e.patient_key = p.patient_key
LEFT JOIN rrt r
  ON e.icu_encounter_key = r.icu_encounter_key
 AND r.charttime >= TRY_CAST(e.period_start AS TIMESTAMP_NTZ) - INTERVAL 6 HOURS
 AND r.charttime <= TRY_CAST(e.period_start AS TIMESTAMP_NTZ) + INTERVAL 1 DAY
```

Keep both inequalities in the `LEFT JOIN`, not in `WHERE`, so all ICU stays
survive.  Group by the ICU identity and identifier values to retain one row
per stay.  The aggregate semantics are:

```sql
MAX(r.dialysis_present) AS dialysis_present,
MAX(r.dialysis_active)  AS dialysis_active,
CASE WHEN COUNT(r.dialysis_type) = 0 THEN CAST(NULL AS VARCHAR(255))
     ELSE STRING_AGG(DISTINCT r.dialysis_type, ', ' ORDER BY r.dialysis_type)
END AS dialysis_type
```

The explicit NULL branch is required: Spark `concat_ws` over an empty set can
otherwise materialize an empty string where source `STRING_AGG` is NULL.

## Output shape, nullability, and oracle check

Using the ICU Encounter and Patient views above and the preprocessed `rrt`
temp view, the exact target aggregation produced:

```text
rows:                 140
distinct stay_id:     140
subject_id non-null:  140/140
stay_id non-null:     140/140
dialysis_present:       6/140 non-null, 134 NULL
dialysis_active:        6/140 non-null, 134 NULL
dialysis_type:          3/140 non-null, 137 NULL
```

The value breakdown was:

```text
dialysis_present dialysis_active dialysis_type   rows
NULL             NULL            NULL            134
1                0               NULL              2
1                1               NULL              1
1                1               CRRT, CVVHDF      1
1                1               IHD                2
```

After normalizing pandas nullable values, the candidate aggregation agreed
with the DuckDB `mimiciv_derived.first_day_rrt` oracle on **140/140 complete
rows and every compared column**.  The ICU identifier/Patient mapping and
`period.start` timestamp check also each agreed on 140/140 rows.

## Code set and discriminator

`first_day_rrt.sql` names no coded filter literals.  Its direct code set is
empty, so there is no target-side `code.coding` system, per-code count, or
codings-per-resource ratio to report.  The RRT itemid systems and counts are
owned by the completed `rrt` dependency and must not be copied into this
consumer or used to rederive it from raw FHIR.  The target discriminates its
only resource stream with the exact ICU Encounter identifier system, not a
`meta.profile` or `Encounter.class` value.

## Gaps and representability

1. **ICU `intime` is a representable FHIR path with a possible upstream
   timestamp transformation.** `Encounter.period.start` is the surviving
   semantic field and is exact for 140/140 demo stays after NTZ casting.  The
   established datetime note says spring-forward-gap wall times may already be
   normalized by the upstream ETL; the original wall time is absent and cannot
   be recovered with an opaque id.  This input is essential in the source
   concept because it controls both inclusive window bounds and therefore row
   inclusion and aggregates.  The measured demo loss is 0/140; a full run must
   bound any affected rows.  This is the known upstream ETL transformation
   case, not permission to block early or to invent a correction.

2. **No source-column gap was measured for `subject_id` or `stay_id`.** Both
   identifier values, all 140 ICU references, and all 140 period starts are
   populated in the authoritative demo.  `icustays.outtime` is not a gap: the
   target SQL never reads it; `period.end` was probed only as unused context.

3. **The RRT dependency's accepted DST divergence is inherited.** The
   completed dependency has a 5,130-row published demo result versus 5,134
   source rows, but the first-day aggregate still matched 140/140 in the
   demonstrated target reconstruction.  The consumer must pass through the
   published dependency and let the full comparator/judge handle any
   inherited full-data effect; it must not repair or rederive RRT.

No resource id was parsed, regenerated, hashed, hardcoded, or used as a
semantic side channel.  No new dataset-wide quirk was established beyond the
already recorded notes, so nothing was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_rrt.md`.

## Fragment reads and verification status

Read `MIMIC_NOTES.d/first_day_bg.md`, `rrt.md`, `crrt.md`,
`icustay_times.md`, and `icustay_detail.md` as provisional sibling leads.
The general datetime, ICU identifier, repeated-chartevent, and opaque-id rules
were checked against the authoritative Delta/dependency probe.  The sibling
fragments' concept-specific full-data claims (including UUID-recovery leads,
lab effects, and quantified ICU full-data loss) were not adopted as facts; no
resource-id recovery was used.  The completed `rrt` attempt 0004 and its
published dependency shape were inspected directly.
