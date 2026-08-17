---
name: fhir-mapping
description: Map MIMIC-IV source tables and columns to MIMIC-on-FHIR resource paths and author FHIR ViewDefinitions using the proven select.column path/name format with forEach/forEachOrNull patterns (from orchestration-new/scripts/sofa_provisioning). Trigger phrases include "FHIR mapping", "map to FHIR", "ViewDefinition", "element path", "FHIRPath".
---

# fhir-mapping

Mapping MIMIC-IV source tables and columns to MIMIC-on-FHIR resource paths
and authoring FHIR ViewDefinitions using the canonical format from
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/`.

**Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md` before mapping anything.** It
records how the served warehouse actually behaves where the StructureDefinition
does not tell you — choice-type fields that split across datatypes row by row
(project one aliased column per variant and COALESCE in the SQL), categorical
values stored as `value.ofType(string)`, codings with a null `display` and the
readable name in `code`, ICU stays identified by `Encounter.identifier.system`
rather than `class`, and elements that are never populated at all. Read the
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/` fragments with it, treating each as
another loop's unconfirmed lead rather than a fact.

When you establish a new dataset-wide quirk, **append** it to this concept's
`MIMIC_NOTES.d/<concept>.md`, keeping the `##` claim / `- Affected:` /
`- Verified:` format so the human's merge is a copy. `MIMIC_NOTES.md` is
read-only while a loop is running; attempt artifacts are immutable.

## ViewDefinition format (authoritative)

The `scripts/sofa_provisioning/v_observation.viewdefinition.json` is the
canonical reference, and the block below is a verbatim copy of it. Every
concept port ViewDefinition MUST follow this exact structural pattern. If the
two ever disagree, the file wins — re-read it rather than trusting this copy.

```json
{
  "resourceType": "ViewDefinition",
  "status": "active",
  "url": "https://fhnaumann.masters/pathling/ViewDefinition/<name>",
  "name": "<name>",
  "resource": "<FHIR_ResourceType>",
  "select": [
    {
      "column": [
        { "path": "getResourceKey()", "name": "observation_id" },
        { "path": "encounter.getReferenceKey(Encounter)", "name": "encounter_id" },
        { "path": "subject.getReferenceKey(Patient)", "name": "patient_id" },
        { "path": "(value).ofType(Quantity).value", "name": "value" },
        { "path": "(value).ofType(Quantity).unit", "name": "unit" },
        { "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }
      ]
    },
    {
      "forEach": "code.coding",
      "column": [
        { "path": "code", "name": "code" },
        { "path": "system", "name": "system" },
        { "path": "display", "name": "display" }
      ]
    }
  ]
}
```

Key format rules:
- `select` is an array of **column groups**. Each group is an object with
  either a `column` array (flat extraction) or a `forEach` + `column` pair
  (iterating over repeating elements).
- Within `column`, each entry has `path` (the FHIRPath expression) and
  `name` (the output column name).
- **NOT** `select.expression` or `select.name` at the object level — that
  shape is hallucinated.
- `forEach`/`forEachOrNull` wraps `code.coding`, `identifier`, etc.

Note what the example does **not** show: `observation_id` and `patient_id` there
are UUID keys, and it emits no `subject_id`/`hadm_id`/`stay_id` at all. Copying
its `getResourceKey()` line into a column named `subject_id` is the standing
mistake — see "Identifier spine" below for the columns a concept output needs.

## How a ViewDefinition becomes a SQL table

There is no registration step to author. The runner materialises each
`ViewDefinition.<label>.json` in the attempt directory as a Spark temp view
named `<label>`, and `concept.sql` selects from those names directly:

```
ViewDefinition.observation.json   ->   SELECT ... FROM observation
```

The filename label is authoritative and must equal the ViewDefinition's own
`name` field — the runner rejects the attempt if they disagree, because the SQL
would otherwise select from a table that was never registered.

`register_patient_sofa.py` in `sofa_provisioning/` predates this and drives a
Pathling server over HTTP. Read its **ViewDefinition JSON** for structure;
ignore its provisioning code.

## FHIRPath idioms (see `mimic-iv/concepts_fhir/MIMIC_NOTES.md`)

- **`getResourceKey()`** — the FHIR resource key. Never an output
  `subject_id`/`hadm_id`/`stay_id`; those come from `identifier.value`. It is
  nonetheless a **required output column in its own right** — see "Identifier
  spine".
- **`getReferenceKey(ResourceType)`** — for foreign-key references
  (e.g. `subject.getReferenceKey(Patient)`, `encounter.getReferenceKey(Encounter)`).
  Also never an output identifier column, and — unlike `getResourceKey()` — not
  an output column at all: emit the key off the resource's own view.
- **`.ofType(X)`** — for choice-type (polymorphic) fields. Each variant
  gets its own column:
  - `(effective).ofType(dateTime)` → `effective_datetime`
  - `(effective).ofType(Period).start` → `effective_period_start`
  - The derived SQL then `COALESCE`s the variants as needed.

Resource and reference keys are **opaque identity only**. Equality joins,
resource grouping/deduplication, and provenance are allowed. Parsing an id,
reconstructing the ETL's UUID algorithm, hashing candidate source values,
hardcoding ids from a comparison report, or using id equality to infer any
timestamp, label, identifier, or clinical value is forbidden. This remains
forbidden when the algorithm is known and candidate enumeration is exact: that
is an ETL implementation side channel, not a FHIR element mapping.

## Identifier spine

**Do not author this from scratch. Copy the block below.** Nearly every concept
needs it, it is the single most common cause of a `shape_fail`, and there is
exactly one correct way to write it.

Three rules, and they are the whole section:

1. `subject_id`, `hadm_id`, `stay_id` come from **`identifier.value`**, never
   from `getResourceKey()` / `getReferenceKey()`. A resource key is not an
   identifier, and no cast makes it one.
2. `identifier.value` is a **string**. The oracle manifest declares these
   columns `INTEGER`. So the SQL always casts. A resource key and an uncast
   digit string both arrive at the gate as `VARCHAR`, and both fail it.
3. Every identifier column is emitted **together with its resource key**. The
   manifest declares them per concept as `key_columns`, and the shape gate
   fails a port that omits one:

   | emit | alongside | from |
   |---|---|---|
   | `subject_id` | `patient_key` | `Patient.getResourceKey()` |
   | `hadm_id` | `encounter_key` | hosp `Encounter.getResourceKey()` |
   | `stay_id` | `icu_encounter_key` | ICU `Encounter.getResourceKey()` |
   | `specimen_id` | `specimen_key` | `Specimen.getResourceKey()` |

   Rule 3 exists because rule 1 used to end "…and must never reach the output",
   which every port followed: they computed the key as their join spine and
   dropped it at the outermost `SELECT`. Derived tables are consumed by a
   downstream SQL-on-FHIR layer that joins on `getResourceKey()` and cannot use
   the integers, so all 36 were unusable to it — and silently, as an empty join
   rather than an error. All 36 were reopened to add the keys.

4. **Reading a derived dependency, join on the key, never on the identifier.**
   A dependency is registered in its *published* shape, which is the shape a
   SQL-on-FHIR server serves: once it emits resource keys, the export drops the
   identifiers those keys replace. So `FROM age` offers `patient_key` and
   `encounter_key`, and no `subject_id` or `hadm_id`. Write:

   ```sql
   LEFT JOIN age AS a ON e.encounter_key = a.encounter_key   -- yes
   LEFT JOIN age AS a ON c.hadm_id = a.hadm_id               -- no: not published
   ```

   The same applies to `GROUP BY`: group a dependency's rows by its key.
   Substitution is safe because the ETL derives the key as
   `uuid_generate_v5(<type namespace>, <identifier>)`, a bijection the shape
   gate already asserts — one identifier has one key, one key has one
   identifier — so nothing about what matches or groups changes.

   Rule 4 exists because `charlson` satisfied rule 3, emitting both keys, and
   still reached `age` through `hadm_id`. Nothing caught it: the runner used to
   register the dependency's *attempt* output, which still had the integers, so
   the join worked at every gate and broke only once exported. The runner now
   registers the published shape, so this fails when you run it.

   **Identifiers stay in `WHERE`.** Rule 4 is about `JOIN` and `GROUP BY` only.
   `WHERE e.hadm_id_str IS NOT NULL` is what selects the hospital stream — the
   Encounter view is unfiltered and returns ICU and ED encounters too, and all
   of them have an `encounter_key`. There is no key form of that filter, and
   rewriting it to `encounter_key IS NOT NULL` silently admits rows from the
   other two streams.

### Emitting a resource key

Three ways to get it wrong, all of which produce a `VARCHAR` column with the
right name:

- **Do not `CAST` it.** It has no manifest type; it is already a Spark STRING.
- **Do not strip the type prefix.** `getResourceKey()` returns
  `Patient/0a8eebfd-a352-522e-89f0-1d4a13abdebc` in *every* position — as a
  primary key and as a reference key alike. That equality is what makes the
  join bind.
- **Do not substitute `Resource.id`.** That is the bare UUID
  (`0a8eebfd-a352-…`), a different value that joins to nothing. The shape gate
  samples the column and rejects anything not in `Type/id` form.

Where the resource's own view is already materialized, take the key from it
(`p.patient_key`, from `getResourceKey()`) rather than from a reference to it.

Where it is **not**, a reference key is equally correct: `getReferenceKey()`
returns the byte-identical value, so `subject.getReferenceKey(Patient)` off an
Encounter or Observation view *is* a valid `patient_key`. Do not add a Patient
view solely to obtain a key you already hold — every stay-grained concept
already materializes an ICU Encounter view for `stay_id`, and that view carries
the patient reference.

Reconstructing a key — `uuid_generate_v5`, hashing, or a literal read off a
comparison report — remains forbidden, and `sql_lint` refuses it. Project the
key; never compute it.

The systems — all four share the same `Patient`/`Encounter` tables, so every
Encounter view must filter on `identifier.system` (unfiltered, the demo
Encounter table is 637 rows against 275 `mimiciv_hosp.admissions`;
`Encounter.class` does not discriminate the streams, see `MIMIC_NOTES.md`):

- `http://mimic.mit.edu/fhir/mimic/identifier/patient` → `subject_id`.
- `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` → `hadm_id`.
- `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` → `stay_id`.
- `http://mimic.mit.edu/fhir/mimic/identifier/encounter-ed` → an ED contact,
  which is **neither** an admission nor an ICU stay.

### The recipe

`ViewDefinition.patient.json` — the UUID to join on, the id to emit:

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str" }
  ]
}
```

`ViewDefinition.encounter.json` — same shape, plus the stream filter:

```json
{
  "column": [
    { "path": "getResourceKey()", "name": "encounter_key" },
    { "path": "subject.getReferenceKey(Patient)", "name": "patient_key" },
    { "path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value", "name": "hadm_id_str" },
    { "path": "period.start", "name": "period_start" }
  ]
}
```

`concept.sql` — join on the keys, emit the cast identifiers **and** the keys:

```sql
SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(e.hadm_id_str   AS INTEGER) AS hadm_id,
    ...
    p.patient_key,                    -- uncast, verbatim, prefix intact
    e.encounter_key
FROM encounter e
JOIN patient p ON e.patient_key = p.patient_key
WHERE e.hadm_id_str IS NOT NULL       -- drops the icu/ed streams
```

The keys go last by convention only — the gate is set-based, so order does not
matter, but it keeps the manifest-shaped prefix readable against
`comparison.full.json`.

The `_str` suffix and the `_key` suffix are load-bearing conventions, not
decoration: a column named `subject_id` inside a ViewDefinition is how the wrong
value reaches the output unnoticed. Keep FHIR-typed columns suffixed until the
final `SELECT` casts them.

An Observation's `subject.getReferenceKey(Patient)` and
`encounter.getReferenceKey(Encounter)` join into these views the same way.
`getResourceKey()` returns a type-prefixed key (`Patient/<uuid>`) and
`getReferenceKey(Patient)` returns the matching form, so the two join directly.

Filtering on `identifier.value IS NOT NULL` selects the stream because the
`where(system=…)` returned nothing for the other two. `forEachOrNull:
"identifier"` with `system`/`value` columns is the alternative shape — use it
only when you genuinely need several systems side by side, since it multiplies
rows per identifier and then needs a pivot.

## Coded filters: constrain inside the `forEach`

A concept's codes are the literals its source SQL names, confirmed against the
data by `fhir-prober`. Nothing translates them — `Observation.code.coding.code`
is a verbatim `CAST(itemid AS TEXT)`, so `CAST(code AS INTEGER)` is the whole
mapping (see `MIMIC_NOTES.md`).

Constrain the coding **inside** the `forEach`, not after it:

```json
{
  "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems')",
  "column": [
    { "path": "code", "name": "item_code" },
    { "path": "system", "name": "code_system" }
  ]
}
```

A bare `forEach: "code.coding"` emits one row per coding. That is currently
harmless because every lab and chart Observation carries exactly one coding —
but the ratio is a property of the warehouse, not of FHIR, and a data
preparation that adds a second coding would double every row feeding a
`full_tuple_multiset` comparison, with nothing in the diff pointing at the
cause. The `where()` form costs nothing and is correct either way.

Discriminate on `system` + exact code. **Never on `meta.profile`** — the merged
data preparation collapses profile values across the Observation sub-profiles,
so a profile that separates streams in one warehouse variant does not in
another.

## MIMIC source-table → FHIR resource mapping

| MIMIC Table (Schema) | Likely FHIR Resource | Required Probe |
|---|---|---|
| `admissions` (hosp) | `Encounter` (`identifier.system` = `…/encounter-hosp`) | id, subject, period, identifier.system |
| `patients` (hosp) | `Patient` | id, birthDate, gender |
| `diagnoses_icd` (hosp) | `Condition` | id, subject, encounter, code, recordedDate |
| `labevents` (hosp) | `Observation` | id, subject, encounter, code, value, effective |
| `microbiologyevents` (hosp) | `Observation` | id, subject, encounter, code, value, effective |
| `prescriptions` (hosp) | `MedicationRequest` | id, subject, encounter, medication, authoredOn |
| `chartevents` (icu) | `Observation` | id, subject, encounter, code, value, effective |
| `inputevents` (icu) | `MedicationAdministration` | id, subject, encounter, medication, effective |
| `outputevents` (icu) | `Observation` | id, subject, encounter, code, value, effective |
| `procedureevents` (icu) | `Procedure` | id, subject, encounter, code, performed |
| `icustays` (icu) | `Encounter` (`identifier.system` = `…/encounter-icu`) | id, subject, period, identifier.system |

## Probing

**Probe the Delta warehouse, not the live server.** Both legs of the loop run
embedded Pathling on Spark over Delta, so that warehouse is the source of
truth. The prod server holds different data (its `Observation` resources carry
the merged profile — see `MIMIC_NOTES.md`) and, more practically, every
resource read on it returns `401`; only `/metadata` is open. Do not spend a
turn on it.

The probe route, which needs no credentials and no network:

```python
import json, os
os.environ.setdefault("PYSPARK_SUBMIT_ARGS",
                      "--driver-memory 4g --conf spark.ui.enabled=false pyspark-shell")
from pathling import PathlingContext

ctx = PathlingContext.create()
ctx.spark.sparkContext.setLogLevel("ERROR")
src = ctx.read.delta(os.environ["MIMIC_FHIR_WAREHOUSE"])

# (a) what fields exist: the encoded Spark schema is the real StructureDefinition
for f in src.read("Encounter").schema.fields:
    print(f.name, "::", str(f.dataType)[:100])

# (b) what is actually populated: materialise a ViewDefinition and count
src.view(json=json.dumps(view_definition)).createOrReplaceTempView("v_probe")
ctx.spark.sql("SELECT count(*), count(<col>) FROM v_probe").show()
```

`src.read("<ResourceType>").schema` answers cardinality/choice-variant
questions faster than a StructureDefinition would, and it describes the data
that will actually be queried. Note that extensions do **not** appear as an
`extension` column — see the extensions entry in `MIMIC_NOTES.md`.

Treat the table above as a starting hypothesis; confirm the populated resource
type, profile, coding system, identifiers, choice variants, and units against
the warehouse. Where a mapping's correctness is checkable against the DuckDB
oracle (`MIMIC_DUCKDB_PATH`), check it — a mapping that looks right in the
schema can still disagree with the oracle row for row.
