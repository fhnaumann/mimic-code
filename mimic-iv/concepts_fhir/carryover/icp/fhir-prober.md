# FHIR prober carryover: `icp`

## Probe provenance

- **Concept:** `icp` (`measurement/icp`), source table `mimiciv_icu.chartevents`.
- **Authoritative warehouse:** `/Users/nau025/warehouses/mimic-iv-demo/delta`, queried with embedded Pathling 9.6.0 on Spark 4.0.2. The live Pathling server was not used.
- **Oracle:** `/Users/nau025/warehouses/mimic4-demo.db`, read-only DuckDB.
- **Probe shape:** Observation ViewDefinition projections used a flat column group plus `forEach: "code.coding"`; the constrained form `code.coding.where(system='<chartevents system>')` also materialized successfully. Patient and Encounter lookup projections were materialized separately.

## Source table to FHIR resource

| MIMIC source table | FHIR resource | Discriminator |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation` | `code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and exact `code` `220765` or `227989`; never use `meta.profile` |

The authoritative Delta has 668,862 chartevents-coded Observation rows/resources. The two target codes occur only under the system above. The warehouse has no served `CodeSystem` resources (`src.read('CodeSystem')` raised `No data found`), so membership must be confirmed from the Observation codings themselves.

## Canonical source-column to FHIRPath mapping

`identifier.value` and materialized choice aliases are strings. The implementer must cast the `_str`/choice aliases in the final SQL to the manifest types; reporting `VARCHAR` here is not completion.

| Source column or derived output | Canonical FHIRPath projection `{path, name}` | FHIR type | Materialized / final target type | Notes and probe count |
|---|---|---|---|---|
| Observation resource identity (internal only) | `{path: "getResourceKey()", name: "observation_id"}` | `id`/resource key | `VARCHAR`; do not emit as a MIMIC id | 313/313 target rows non-null. The source SQL has no event PK; the ETL UUID is an internal row key. |
| `subject_id` join spine | `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` | `Reference(Patient)` key | `VARCHAR`; join to Patient | 313/313 target rows non-null and joined to `Patient.getResourceKey()`. |
| `subject_id` output value | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` on the Patient view | `Identifier.value` string | `VARCHAR` in the view, then `CAST(... AS INTEGER)` | 100/100 demo Patients had the identifier; the target Observation→Patient lookup returned 313/313. |
| `stay_id` join spine | `{path: "encounter.getReferenceKey(Encounter)", name: "encounter_key"}` | `Reference(Encounter)` key | `VARCHAR`; join to Encounter | 313/313 target rows non-null and joined to an ICU Encounter. |
| `stay_id` output value | `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` on the Encounter view | `Identifier.value` string | `VARCHAR` in the view, then `CAST(... AS INTEGER)` | The all-Encounter projection had 140/637 ICU identifier values; after the Observation join the target was 313/313. Filter the ICU identifier/system (or `stay_id_str IS NOT NULL`) so hosp/ED Encounter streams do not mix in. |
| `itemid` filter | Inside `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')"`: `{path: "code", name: "code"}` | `Coding.code` string | `VARCHAR`; compare exact strings before any integer cast | Target code rows: `220765` 302/302 and `227989` 11/11. `CAST(code AS INTEGER)` recovers itemid only after the system filter. |
| Coded-system discriminator | Inside the same coding `forEach`: `{path: "system", name: "system"}` | `uri` string | `VARCHAR` | 313/313 non-null; exact target system above. Target coding/resource ratio is 313/313 = 1.0. |
| Coding display (not a source output) | Inside the same coding `forEach`: `{path: "display", name: "display"}` | string | `VARCHAR` | 313/313 non-null; displays are `Intra Cranial Pressure` (302) and `Intra Cranial Pressure #2` (11). Use code/system, not display, for filtering. |
| `charttime` | `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` | `dateTime` | Pathling alias is string/VARCHAR; final output `TIMESTAMP_NTZ` | 313/313 non-null. `effective.ofType(Period).start/end` were 0/313 and `effective.ofType(instant)` was 0/313. `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` preserved the source wall time in the 313-row pandas comparison; do not use an offset-aware cast or final plain `TIMESTAMP`. |
| `valuenum` / FHIR numeric value | `{path: "(value).ofType(Quantity).value", name: "quantity_value"}` | `Quantity.value` decimal | Pathling ViewDefinition alias is string/VARCHAR; cast to `FLOAT`/`DOUBLE` before the CASE and `MAX`; final `icp` must be manifest `FLOAT` | 313/313 target rows had Quantity values and 0/313 had `value.ofType(string)`. Raw Delta `valueQuantity.value` is `decimal(32,6)`. |
| `valueuom` (not selected by canonical SQL; sanity-check only) | `{path: "(value).ofType(Quantity).unit", name: "quantity_unit"}` | `Quantity.unit` string | `VARCHAR` | 313/313 non-null, all `mmHg`. It need not be emitted by `icp`. |
| Derived `icp` | Aggregate `MAX(CASE WHEN CAST(quantity_value AS FLOAT) > 0 AND CAST(quantity_value AS FLOAT) < 100 THEN CAST(quantity_value AS FLOAT) ELSE NULL END)` over `(subject_id, stay_id, charttime)` | `FLOAT` | final `FLOAT` | The strict source range is load-bearing: 297/313 rows valid, 16/313 invalid (`14` negative/zero rows for 220765 and `2` zero rows for 227989); 14/303 groups have only invalid values and remain with NULL `icp`. |

The source `value` text column is not an output column. In the selected demo rows it was non-null for 313/313 and `valuenum` was non-null for 313/313, so the FHIR target used Quantity for every selected row. If a selected source row has `valuenum IS NULL`, the chartevents ETL's alternate representation is `Observation.value.ofType(string)`, not a numeric Quantity.

## Confirmed code set and coding cardinality

- Source Oracle target: 313 rows total; item `220765`: 302 rows; item `227989`: 11 rows.
- Source valid-range counts: `220765` 288 and `227989` 9; source invalid-or-NULL counts: `220765` 14 and `227989` 2.
- FHIR target system/code counts: `220765` 302 rows/resources and `227989` 11 rows/resources. No occurrence of either literal under another system was observed.
- Coding projection over all Observation codings gave 813,540 coding rows / 813,540 distinct Observation resources; the target stream gave 313 / 313, ratio **1.0 coding per resource**. A constrained coding `forEach` is still required by convention.
- The discriminator is `system + exact code`. `meta.profile` is deliberately not used because merged warehouse preparation can collapse subtype profiles; the base binding above is stable in the authoritative Delta.

## Identifier, datetime, value, and duplicate/group checks

- Observation→Patient and Observation→ICU Encounter lookup agreement was 313/313 for both numeric identifiers. The 313-row pandas comparison of `(subject_id, stay_id, charttime, code, value)` as a multiset was exact: **313/313**, with no null lookup ids.
- Source grouping has 303 `(subject_id, stay_id, charttime)` groups, including 10 groups with two rows. Every multi-row group is the two ICP itemids at the same timestamp; there are no same-code duplicates in this target. The FHIR target has the same 303 groups, 10 multi-row groups, maximum group size 2, and 302/302 plus 11/11 per-code rows. Do not group by itemid; apply the final `MAX` across both codes.
- After applying the source range CASE to the FHIR Quantity, the final aggregate agreed with the DuckDB oracle on **303/303** groups, including 14 NULL-only groups.
- The source target had no NULL `value` rows and the hard-coded ETL duplicate tuple `(stay_id=34934165, charttime='2151-10-03 05:14:00')` occurred 0 times, so the demo target had no row loss from either global chartevents ETL predicate. This does not make the predicates safe to ignore for full data.

## Representability gaps

| Gap | Classification | Consequence |
|---|---|---|
| Observation has no direct numeric `subject_id` or `stay_id` element | absent but derivable | Recover through `subject.getReferenceKey(Patient)` → Patient patient identifier and `encounter.getReferenceKey(Encounter)` → ICU Encounter stay identifier. Exact for 313/313 demo target rows. |
| Pathling materializes FHIR `dateTime` and Quantity value aliases as strings | absent as a native output type but derivable by cast | Cast `effective_datetime` to `TIMESTAMP_NTZ` and `quantity_value` to `FLOAT` before aggregation; measured exact on all 313 rows and 303 groups. |
| Chartevents ETL excludes source rows with `value IS NULL` before creating Observation resources, and excludes one hard-coded duplicate tuple | not representable for an omitted event | There is no FHIR resource/path from which to recover an omitted source row. This ICP demo has 0 affected rows (source `value IS NULL` 0/313; duplicate tuple 0), so measured target agreement is unaffected. |
| `valuenum IS NULL` source rows, if encountered, are represented by `valueString`, not Quantity | absent but derivable only as text; numeric recovery is not guaranteed | Do not coerce `value.ofType(string)` into numeric ICP. No such ICP row occurs in the demo (0/313). |

No concept-specific approximation was needed. The only measured target comparison was exact; no claim is made that the ETL omission gap can be inverted outside the observed target.

## Notes/fragments used

`MIMIC_NOTES.md` entries that changed this mapping decision were: Delta (not stale NDJSON) is authoritative; itemid-derived Observation codes are verbatim and must be filtered by system + exact code; MIMIC ids are string `identifier.value` values while resource/reference keys are UUIDs; Quantity.value ViewDefinition aliases are VARCHAR-like; FHIR datetimes carry offsets and must be parsed as `TIMESTAMP_NTZ`; Observation subtype profile must not be used as a discriminator; categorical chartevents use `valueString` (checked here as empty for ICP); and the one-coding-per-lab/chart Observation cardinality must be measured (here 1.0).

All fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/` were read: `README.md`, `arb.md`, `blood_differential.md`, `cardiac_marker.md`, `chemistry.md`, `code_status.md`, `coagulation.md`, `complete_blood_count.md`, `crrt.md`, `dobutamine.md`, `dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`, and `icp.md`. The ICP fragment's chartevents ETL-omission lead was verified against the ETL SQL and the target counts. The other fragments were treated as provisional leads; their concept-specific counts were not reused as facts. Chartevents-related leads were independently checked only for this ICP target (system/code, Quantity/string, effective choice, and duplicate/group behavior).
