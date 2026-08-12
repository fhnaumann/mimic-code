# FHIR probe mapping: inflammation

## Scope and source semantics

- Concept: `inflammation`
- Source table: `mimiciv_hosp.labevents` only.
- Source executable code filter: `itemid = 50889`.
- The `51652` literal in the source SQL is commented out and is not an
  executable filter. It has 0 demo rows when queried directly.
- Source row predicate: `valuenum IS NOT NULL AND valuenum > 0`.
- Source aggregate: `GROUP BY specimen_id`, with independent `MAX` values for
  `subject_id`, `hadm_id`, `charttime`, and `valuenum` (the latter emitted as
  `crp`).
- Natural key: `specimen_id`.
- Oracle output types: `subject_id INTEGER`, `hadm_id INTEGER`,
  `charttime TIMESTAMP`, `specimen_id INTEGER`, `crp DOUBLE`.

## Resource mapping

`mimiciv_hosp.labevents` maps to FHIR `Observation`, specifically the
itemid-derived laboratory Observation stream identified by
`code.coding.system` plus exact `code`. Do not discriminate using
`meta.profile`.

The source `specimen_id` is carried by a separate FHIR `Specimen` resource.
Join `Observation.specimen.getReferenceKey(Specimen)` to
`Specimen.getResourceKey()`, then read the lab identifier. The source
`subject_id` is likewise read through the Patient resource, and source
`hadm_id` through the hospital Encounter resource when the Observation has an
`encounter` reference.

## Canonical ViewDefinition projections

These are the exact `select[].column[].{path,name}` projections to use. The
identifier values and all materialized FHIR choice aliases are FHIR strings;
the implementer's final SQL must cast the numeric output columns to the
manifest types.

### Observation (`resource: Observation`)

```json
{
  "select": [
    {
      "column": [
        {"path": "getResourceKey()", "name": "observation_key"},
        {"path": "subject.getReferenceKey(Patient)", "name": "patient_key"},
        {"path": "encounter.getReferenceKey(Encounter)", "name": "encounter_key"},
        {"path": "specimen.getReferenceKey(Specimen)", "name": "specimen_key"},
        {"path": "(effective).ofType(dateTime)", "name": "effective_datetime"},
        {"path": "(value).ofType(Quantity).value", "name": "quantity_value"},
        {"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"},
        {"path": "(value).ofType(Quantity).comparator", "name": "quantity_comparator"},
        {"path": "(value).ofType(string)", "name": "value_string"}
      ]
    },
    {
      "forEach": "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems' and code='50889')",
      "column": [
        {"path": "code", "name": "code"},
        {"path": "system", "name": "system"},
        {"path": "display", "name": "display"}
      ]
    }
  ]
}
```

The filter belongs inside `forEach`; a bare coding iteration is safe in the
current warehouse only because the measured coding/resource ratio is 1.0.
The `observation_key` and any `labevent_id` identifier are probe/provenance
columns, not output columns for this aggregate.

### Patient (`resource: Patient`)

```json
{
  "select": [
    {"column": [{"path": "getResourceKey()", "name": "patient_key"}]},
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient')",
      "column": [{"path": "value", "name": "subject_id_str"}]
    }
  ]
}
```

Use `patient_key` for the join and `CAST(subject_id_str AS INTEGER)` for the
final `subject_id`. `getResourceKey()` is a UUID, not the MIMIC subject ID.

### Hospital Encounter (`resource: Encounter`)

```json
{
  "select": [
    {"column": [{"path": "getResourceKey()", "name": "encounter_key"}]},
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp')",
      "column": [{"path": "value", "name": "hadm_id_str"}]
    }
  ]
}
```

Use `encounter_key` for the Observation join and
`CAST(hadm_id_str AS INTEGER)` for `hadm_id`. The join must be a LEFT JOIN;
an Observation without an encounter is not evidence that the source row did
not have a `hadm_id`.

### Lab Specimen (`resource: Specimen`)

```json
{
  "select": [
    {"column": [{"path": "getResourceKey()", "name": "specimen_key"}]},
    {
      "forEach": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab')",
      "column": [{"path": "value", "name": "specimen_id_str"}]
    }
  ]
}
```

`CAST(specimen_id_str AS INTEGER)` is the output `specimen_id` and the
grouping key. `forEachOrNull` is not needed for this concept: every served lab
Specimen has one matching filtered identifier in the probe. If a reusable
view must retain resources with no matching identifier, the alternative is
`forEachOrNull: "identifier.where(system='.../identifier/specimen-lab')"`
with `{path: "value", name: "specimen_id_str"}`.

## Source-column to FHIRPath mapping

| Source column / semantics | FHIR resource and canonical path | Alias / FHIR type | Mapping notes |
|---|---|---|---|
| `itemid` filter `50889` | `Observation.code.coding` via `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems' and code='50889')"`; column path `code` | `code`; `string` | Served code is the unchanged string `50889`. |
| coding system | Same coding `forEach`; column path `system` | `system`; `string` | Exact system: `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`. |
| item display (not source output) | Same coding `forEach`; column path `display` | `display`; `string` | Demo target display is `C-Reactive Protein`; do not use display as discriminator. |
| `valuenum` and positive predicate | `(value).ofType(Quantity).value` | `quantity_value`; materialized `string`, final `DOUBLE` | Cast before `> 0` and before output. For target code, 42/44 are Quantity values and exactly the 42 source non-null positive rows. |
| source value unit (not output) | `(value).ofType(Quantity).unit` | `quantity_unit`; `string` | Demo target `mg/L` on 42/44 Quantity rows. |
| comparator safeguard | `(value).ofType(Quantity).comparator` | `quantity_comparator`; `string` | 0/44 target rows. Do not admit comparator/text-synthesized values as source `valuenum` rows. |
| source `charttime` | `(effective).ofType(dateTime)` | `effective_datetime`; materialized `string`, final `TIMESTAMP_NTZ` | 44/44 target rows populated; cast directly to `TIMESTAMP_NTZ`, never offset-normalize with `to_timestamp` in a local timezone. Aggregate the cast value with `MAX` by specimen. |
| source `specimen_id` | `Observation.specimen.getReferenceKey(Specimen)` → `Specimen.getResourceKey()`; then `Specimen.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value` | `specimen_key`, then `specimen_id_str`; key `string`, identifier `string`, final `INTEGER` | 44/44 Observation references resolved to the matching lab Specimen identifier. Group on the cast identifier. |
| source `subject_id` | `Observation.subject.getReferenceKey(Patient)` → `Patient.getResourceKey()`; then `Patient.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value` | `patient_key`, then `subject_id_str`; key `string`, identifier `string`, final `INTEGER` | 44/44 target subjects resolved exactly. |
| source `hadm_id` | `Observation.encounter.getReferenceKey(Encounter)` → `Encounter.getResourceKey()`; then `Encounter.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value` | `encounter_key`, then `hadm_id_str`; key `string`, identifier `string`, final nullable `INTEGER` | 26/44 target Observations have hospital Encounter references; among the 42 positive source rows, 24/42 do. The 18 positive rows with source `hadm_id IS NULL` have no encounter reference. Use LEFT JOIN. |
| source `labevent_id` (not selected by source SQL) | `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/observation-labevents').value` | `labevent_id_str`; `string` | Optional provenance column only; not part of the inflammation output. |

## Confirmed coding and cardinality results

The authoritative demo Delta path used was
`/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with embedded Pathling
9.6.0 / Spark 4.0.2. The target coding was confirmed from served Delta data,
not the stale NDJSON or a terminology service.

- `system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`,
  `code = '50889'`: 44 coding rows, 44 distinct Observation resources,
  codings/resource = `1.0`.
- Source DuckDB `itemid=50889`: 44 rows total, 42 with non-null positive
  `valuenum`, 2 with NULL `valuenum`, 0 zero, 0 negative. Direct `itemid=51652`
  count is 0; it is commented out and not an executable code.
- Target values: Quantity 42/44, valueString 2/44 (`___`), comparator 0/44,
  effective dateTime 44/44, subject reference 44/44, specimen reference
  44/44, encounter reference 26/44. Both valueString rows are excluded by
  the source numeric predicate.
- All 42 source-positive rows have a distinct specimen in the demo: 42 source
  groups, maximum one qualifying row per group, and 42 FHIR specimen groups.
- The exact FHIR grouping replay agreed with the DuckDB aggregate for 42/42
  groups on `MAX(subject_id)`, `MAX(hadm_id)`, `MAX(charttime)`, and `MAX(crp)`.
  Subject, specimen, charttime, and CRP agreement were each 42/42; hadm was
  42/42 when the nullable group result was compared.
- Identifier columns materialized as `string`: Patient `subject_id_str`
  100/100 non-null, hospital Encounter `hadm_id_str` 275/275 non-null, and
  lab Specimen `specimen_id_str` 11,122/11,122 non-null. The final SQL must
  cast them to the manifest's integer output types.

## Gaps and lossy transformations

- `subject_id` and `specimen_id`: no observed gap in the target demo; both are
  exactly recoverable through the identifier spines above. They are strings in
  FHIR and require final integer casts.
- `hadm_id`: exactly recoverable when the Observation encounter reference is
  present. If a lab Observation lacks that reference while the relational
  source has a hadm, it is **absent and only approximable** from patient plus
  effective time and hospital Encounter periods; that heuristic was not
  exercised for positive 50889 rows (0 such demo rows), so no target accuracy
  claim is made. Do not manufacture the value; retain a nullable output and
  LEFT JOIN. The target demo had 24/24 positive source non-null hadm values
  represented by Encounter references.
- `charttime`: `effectiveDateTime` is the only populated effective variant for
  target 50889 (44/44; Period and instant variants 0/44). Normal parsing by
  `TIMESTAMP_NTZ` exactly preserved all 44 demo wall-clock values, and the
  target had 0 March DST-gap 02:xx rows. Nevertheless, the upstream FHIR ETL
  casts lab chart times through `TIMESTAMPTZ`; a spring-forward gap time is
  irreversibly normalized before serialization. Such a source time is **not
  representable exactly** from the served effective value. This is the
  established dataset-wide DST limitation, not a reason to use an
  offset-aware local-time cast.
- `valuenum`: the served Quantity is a faithful target representation for all
  42 qualifying rows in the demo. Labevents ETL can synthesize a Quantity from
  comparator text when source `valuenum` is NULL, and can fall back to
  `valueString`/comments; those paths are **not equivalent** to source
  `valuenum`. For this code there were no comparator-bearing rows and the two
  nonnumeric fallback rows were visible as `___`, so the source filter is
  exactly reproduced by the positive Quantity branch in the probe.

## Probe provenance

- Read source carryover exactly: `carryover/inflammation/source-analyst.md` and
  `carryover/inflammation/carryover.json`.
- Read the canonical ViewDefinition:
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md` before probing and read every
  fragment present in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/` at attempt 0001:
  `arb.md`, `blood_differential.md`, `cardiac_marker.md`, `chemistry.md`,
  `code_status.md`, `coagulation.md`, `complete_blood_count.md`, `crrt.md`,
  `dobutamine.md`, `dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`,
  `icp.md`, `icustay_detail.md`, and `README.md`. These fragments were
  provisional leads; the item 50889 claims used here were independently
  checked against served Delta and DuckDB.
- Read ETL provenance: `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_labevents.sql`
  and `/Users/nau025/Documents/mimic-fhir/sql/fhir_specimen_lab.sql`.
- Embedded probe command family: `uv run python` with
  `mimic_utils.embedded_runner.EmbeddedExecutor`, materializing the four
  ViewDefinitions above over the demo Delta; raw schemas, materialized types,
  counts, code systems, identifier resolution, value branches, and effective
  variants were counted.
- DuckDB probe command family: `uv run python` with read-only
  `duckdb.connect('/Users/nau025/warehouses/mimic4-demo.db', read_only=True)`;
  it counted the source predicate, dead/commented literal, specimen groups,
  and compared all 44 target labevent IDs plus the 42 aggregate groups.

No new dataset-wide quirk was found beyond claims already established in
`MIMIC_NOTES.md`; `mimic-iv/concepts_fhir/MIMIC_NOTES.d/inflammation.md` was
therefore not created or appended.
