# FHIR mapping: `ventilation`

## Probe basis and scope

- Source analysis: `mimic-iv/concepts_fhir/carryover/ventilation/source-analyst.md`.
- Canonical SQL read: `mimic-iv/concepts/treatment/ventilation.sql`.
- Dependency SQLs read: `mimic-iv/concepts/measurement/oxygen_delivery.sql` and
  `mimic-iv/concepts/measurement/ventilator_setting.sql`.
- Canonical ViewDefinition structure read:
  `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/v_observation.viewdefinition.json`.
- Authoritative warehouse: `/Users/nau025/warehouses/mimic-iv-demo/delta`,
  queried with embedded Pathling 9.6.0/Spark 4.0.2. Probes pinned
  `MIMIC_SPARK_TIMEZONE=UTC`, matching `src/mimic_utils/embedded_runner.py`.
- Read-only oracle: `/Users/nau025/warehouses/mimic4-demo.db`.
- No live Pathling server was used. No resource id was parsed, regenerated,
  hashed, hardcoded, or used to infer a source value.

`ventilation.sql` has no direct raw-table read and no FHIR code filter. Its
physical inputs are the published dependency views `oxygen_delivery` and
`ventilator_setting`. The raw FHIR source for both dependencies is
`mimiciv_icu.chartevents`, represented by `Observation` resources.

## Published dependency boundary

The source analyst's SQL interface names the relational columns `stay_id`,
`charttime`, the four oxygen-device slots, and the two ventilator-mode slots.
The completed dependency attempts additionally emit the resource keys. The
runner's published-dependency preprocessing applies the identifier strip:
`strip_mimic_ids()` dropped `subject_id` and `stay_id` from both dependency
outer projections because their paired resource keys are present. Therefore
the relation actually available to ventilation through `FROM oxygen_delivery`
and `FROM ventilator_setting` is:

| Published dependency column | FHIR/provenance | Published type | Ventilation use |
|---|---|---|---|
| `patient_key` | Patient/resource reference key, opaque | `STRING` | Patient grouping/provenance and required final key |
| `icu_encounter_key` | ICU Encounter/resource reference key, opaque | `STRING` | Event-grid key, dependency joins, partition scope, required final key |
| `charttime` | `Observation.effectiveDateTime` | `TIMESTAMP_NTZ`/`TIMESTAMP` | Event-grid key, equality joins, ordering, episode boundaries |
| `o2_flow` | oxygen dependency numeric pivot | `FLOAT` | Not consumed by ventilation; retained by the dependency interface |
| `o2_flow_additional` | oxygen dependency numeric pivot | `FLOAT` | Not consumed by ventilation |
| `o2_delivery_device_1`–`_4` | ranked `226732` categorical text slots | `VARCHAR`/`STRING` | All oxygen-device CASE branches |
| numeric ventilator-setting outputs | numeric dependency pivots | `FLOAT` | Not consumed by ventilation |
| `ventilator_mode` | `223849` text pivot | `VARCHAR`/`STRING` | Invasive-ventilation CASE branch |
| `ventilator_mode_hamilton` | `229314` text pivot | `VARCHAR`/`STRING` | Invasive and non-invasive Hamilton CASE branches |
| `ventilator_type` | `223848` text pivot | `VARCHAR`/`STRING` | Not consumed by ventilation |

The published shape has no `subject_id` or `stay_id`. Do not join the two
dependencies on an integer that is absent from the published relation and do
not infer one from an opaque UUID. Build the event grid and joins on
`icu_encounter_key` plus `charttime`. If the final ventilation result must
emit the manifest's integer `stay_id`, join `icu_encounter_key` to an ICU
Encounter view and read the ICU identifier value shown below.

The checked-in dependency attempts confirm the same key contract: the
attempt-shaped oxygen output contains `patient_key` and `icu_encounter_key`,
and the attempt-shaped ventilator output contains those two keys; the
published strip drops only `subject_id` and `stay_id` (`uv run` probe of
`strip_mimic_ids`, 2026-08-25). The full dependency comparisons were exact:
oxygen attempt_0004 `601,546/601,546`, ventilator_setting attempt_0002
`1,006,127/1,006,127`.

## Source table to FHIR resource

| MIMIC-IV source table | FHIR resource | Discriminator |
|---|---|---|
| `mimiciv_icu.chartevents` | `Observation` | `code.coding.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'` plus exact `code.coding.code`; never `meta.profile` |
| dependency `oxygen_delivery` | published derived relation, not a FHIR resource | `icu_encounter_key` + `charttime`; do not rederive in ventilation |
| dependency `ventilator_setting` | published derived relation, not a FHIR resource | `icu_encounter_key` + `charttime`; do not rederive in ventilation |
| ICU stay identity | `Encounter` with ICU identifier system | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'` |
| patient identity | `Patient` | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/patient'` |

## Canonical source-column to FHIRPath mapping

The first group below is the reusable Observation extraction. A target
ViewDefinition should constrain the coding inside `forEach`, as in the
canonical observation ViewDefinition, and should use `forEachOrNull` for the
optional component.

| Source column / role | Canonical `{path, name}` | FHIR type | Pathling materialized type / target requirement | Probe count and use |
|---|---|---|---|---|
| Observation identity | `{"path": "getResourceKey()", "name": "observation_key"}` | resource key `string` | `STRING`; opaque only | 19,224/19,224 non-null; cardinality/provenance only |
| `chartevents.subject_id` join key | `{"path": "subject.getReferenceKey(Patient)", "name": "patient_key"}` | Patient `Reference` key | `STRING`, type-prefixed; never cast or parse | 19,224/19,224 non-null; equality join only |
| `chartevents.subject_id` value | `{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", "name": "subject_id_str"}` on `Patient` | `Identifier.value` `string` | `STRING`; cast to manifest `INTEGER` only in final SQL | Patient view 100/100; Observation-to-Patient join 19,224/19,224 |
| `chartevents.stay_id` join key | `{"path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key"}` | ICU Encounter `Reference` key | `STRING`, type-prefixed; equality join only | 19,224/19,224 non-null; 138 distinct target ICU encounters |
| `chartevents.stay_id` value | `{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"}` on the ICU `Encounter` view | `Identifier.value` `string` | `STRING`; cast to manifest `INTEGER` only in final SQL | ICU Encounter view 140/140; Observation-to-ICU-Encounter/stay join 19,224/19,224 |
| ICU identifier discriminator | `{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').system", "name": "stay_system"}` | `Identifier.system` `uri` | `STRING` | All 140 ICU Encounter rows selected by the `encounter-icu` system; `Encounter.class` is not used |
| `chartevents.charttime` | `{"path": "(effective).ofType(dateTime)", "name": "effective_datetime"}` | FHIR `dateTime` | Pathling `STRING`; cast with `TRY_CAST(... AS TIMESTAMP_NTZ)` | 19,224/19,224 non-null; source/FHIR effective wall-time tuples agreed 19,224/19,224 in the rebuilt demo |
| choice-type check | `{"path": "(effective).ofType(Period).start", "name": "effective_period_start"}` | FHIR `dateTime` | `STRING` | 0/19,224; do not rely on this variant for this stream |
| choice-type check | `{"path": "(effective).ofType(instant)", "name": "effective_instant"}` | FHIR `instant` | native `TIMESTAMP` | 0/19,224; do not coalesce this with the dateTime string |
| source `chartevents.valuenum` | `{"path": "(value).ofType(Quantity).value", "name": "quantity_value"}` | `Quantity.value` `decimal` | ViewDefinition alias `STRING`; cast to `DOUBLE` before numeric pivots/cleaning, then dependency output `FLOAT` | 15,656/19,224 overall (14,408/14,831 in the ventilator-setting subset); exact per-code counts below |
| source `chartevents.valueuom` | `{"path": "(value).ofType(Quantity).unit", "name": "quantity_unit"}` | `Quantity.unit` `string` | `STRING`; not consumed by ventilation | 11,591/19,224 overall; dependency source outputs do not expose it |
| categorical `value` where `valuenum` is NULL | `{"path": "(value).ofType(string)", "name": "value_string"}` | `valueString` `string` | `STRING`; use for direct text fallback | 3,568/19,224 overall, consisting of 3,145 item `226732`, 386 item `223848`, and 37 item `223849` |
| numeric-row ventilator text | `{"path": "value.ofType(string)", "name": "component_text"}` inside `forEachOrNull: "component"` | `Observation.component.valueString` `string` | `STRING`; use only when component code/system match the parent item | 2,319/19,224; 906/1,292 for `223848`, 1,011/1,048 for `223849`, 402/402 for `229314` |
| component discriminator | `{"path": "code.coding.code", "name": "component_item_code"}` inside `forEachOrNull: "component"` | `Coding.code` `string` | `STRING` | 2,319/2,319 component rows matched the parent item code |
| component binding | `{"path": "code.coding.system", "name": "component_system"}` inside `forEachOrNull: "component"` | `Coding.system` `uri` | `STRING` | 2,319/2,319 matched the chartevents URI |
| item discriminator | `{"path": "code", "name": "code"}` inside `forEach: "code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items')"` | `Coding.code` `string` | `STRING`; exact source itemid text | 19,224/19,224 non-null |
| item binding | `{"path": "system", "name": "system"}` in the same constrained coding group | `Coding.system` `uri` | `STRING` | 19,224/19,224; one distinct system |
| item display | `{"path": "display", "name": "display"}` in the same constrained coding group | `Coding.display` `string` | `STRING`; descriptive only, never a filter | 19,224/19,224 non-null |
| source `chartevents.storetime` for oxygen ranking | `{"path": "issued", "name": "issued"}` | FHIR `instant` | native Spark `TIMESTAMP`; not a published dependency column | 4,393/4,393 oxygen resources non-null; use the FHIR value for the dependency's ranking, never infer it from an id |

The source identifiers remain strings in the FHIR extraction. The final
manifest target types are `INTEGER` for `subject_id`/`stay_id`, `TIMESTAMP`
for `charttime`/`starttime`/`endtime`, `FLOAT` for dependency numeric values,
and `VARCHAR` for device/mode/status text. Keys remain uncast `STRING`s with
their `Patient/` or `Encounter/` prefix.

## Exact source itemids, systems, and served counts

Ventilation itself names no raw itemid. Its two dependency SQLs name exactly
the following `chartevents.itemid` literals:

```text
oxygen_delivery: 223834, 227582, 227287, 226732
ventilator_setting: 224688, 224689, 224690, 224687, 224685, 224684,
                    224686, 224696, 220339, 224700, 223835, 223849,
                    229314, 223848, 224691
```

The served discriminator is the single observed system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` plus the
exact code. There were 19,224 coding rows and 19,224 distinct Observation
resources: the codings-per-resource ratio was `19,224 / 19,224 = 1.000`, and
the ratio was 1.000 for every code. No profile predicate was used.

| Exact code | Source rows after the dependency input predicate | FHIR coding rows / distinct resources | Ratio | Quantity | direct `valueString` | component text |
|---:|---:|---:|---:|---:|---:|---:|
| 220339 | 1,447 | 1,447 / 1,447 | 1.000 | 1,447 | 0 | 0 |
| 223834 | 1,090 | 1,090 / 1,090 | 1.000 | 1,090 | 0 | 0 |
| 223835 | 1,746 | 1,746 / 1,746 | 1.000 | 1,746 | 0 | 0 |
| 223848 | 1,292 | 1,292 / 1,292 | 1.000 | 906 | 386 | 906 |
| 223849 | 1,048 | 1,048 / 1,048 | 1.000 | 1,011 | 37 | 1,011 |
| 224684 | 769 | 769 / 769 | 1.000 | 769 | 0 | 0 |
| 224685 | 1,331 | 1,331 / 1,331 | 1.000 | 1,331 | 0 | 0 |
| 224686 | 661 | 661 / 661 | 1.000 | 661 | 0 | 0 |
| 224687 | 1,359 | 1,359 / 1,359 | 1.000 | 1,359 | 0 | 0 |
| 224688 | 801 | 801 / 801 | 1.000 | 801 | 0 | 0 |
| 224689 | 1,314 | 1,314 / 1,314 | 1.000 | 1,314 | 0 | 0 |
| 224690 | 1,331 | 1,331 / 1,331 | 1.000 | 1,331 | 0 | 0 |
| 224691 | 330 | 330 / 330 | 1.000 | 330 | 0 | 0 |
| 224696 | 510 | 510 / 510 | 1.000 | 510 | 0 | 0 |
| 224700 | 490 | 490 / 490 | 1.000 | 490 | 0 | 0 |
| 226732 | 3,145 | 3,145 / 3,145 | 1.000 | 0 | 3,145 | 0 |
| 227287 | 145 | 145 / 145 | 1.000 | 145 | 0 | 0 |
| 227582 | 13 | 13 / 13 | 1.000 | 13 | 0 | 0 |
| 229314 | 402 | 402 / 402 | 1.000 | 0 | 0 | 402 |
| **total** | **19,224** | **19,224 / 19,224** | **1.000** | **15,656** | **3,568** | **2,319** |

All 19 source code filters are present; no lifted itemid has a zero count.
The source `value IS NOT NULL` and `stay_id IS NOT NULL` predicates retained
all 14,831 ventilator-setting rows; oxygen's four target code streams also had
no NULL `value` or `stay_id` rows in this demo target. The FHIR code and source
row counts agreed 19,224/19,224.

## Dependency value reconstruction and repeated-row cardinality

The component branch is required for the three textual ventilator-setting
items. The canonical reconstruction is:

```text
text_for_223848 = component_text where component_system/code match 223848,
                   else value_string
text_for_223849 = component_text where component_system/code match 223849,
                   else value_string
text_for_229314 = component_text where component_system/code match 229314,
                   else value_string
```

The source/FHIR text pivots agreed exactly on all 2,742 source groups for
`223848`, `223849`, and `229314`. The observed component text includes
`Drager`, `Avea`, `Other` for `223848`; ventilator-mode labels for `223849`;
and Hamilton labels for `229314`. Do not read the source text from a resource
id. Numeric `valuenum` comes from Quantity.value and the dependency's FIO2 and
PEEP cleaning is applied after casting it from the materialized string.

The FHIR stream is one Observation per retained source chartevents row for
these codes, not one row per `(stay_id, charttime, itemid)` group. Counts from
the authoritative probe were:

| Code | `(patient, time)` groups | groups with repeats | maximum resources in a group |
|---:|---:|---:|---:|
| 226732 | 3,014 | 106 | 3 |
| each of the other 18 codes | equal to its resource count | 0 | 1 |

The oxygen dependency must therefore rank repeated `226732` resources before
pivoting slots; it must not pre-deduplicate them. It uses
`issued` (the FHIR representation of source `storetime`) for that ranking.
The ventilator-setting dependency groups by patient and charttime and uses
MAX pivots, so its final demo grain was 2,064 groups from 14,831 raw target
rows. The oxygen dependency final demo grain was 1,154 groups from 4,393 raw
target rows. Replaying both dependency SQL interfaces from the FHIR
projections and the DuckDB source gave 1,154/1,154 oxygen groups with all
published values equal, and 2,064/2,064 ventilator groups with exact text and
numeric agreement within the dependency comparator tolerance.

The `issued` caveat is bounded: direct duplicate-aware source `storetime` lists
were not wall-clock-identical on 1,623/4,262 oxygen `(subject, stay, time,
item)` groups under the UTC Spark read, but the dependency's ranked/pivoted
output still agreed 1,154/1,154 in the demo and the completed full oxygen
attempt_0004 comparison was exact. This is a dependency ranking concern, not
a reason to recover a value from an opaque id.

## Exact ventilation status literals and observed source counts

These are dependency-output string filters, not FHIR code filters. The CASE
priority is `Tracheostomy` > `InvasiveVent` > `NonInvasiveVent` > `HFNC` >
`SupplementalOxygen` > `None`; unmatched rows become NULL and are removed.
Trailing spaces shown below are significant.

Oxygen-device literals:

```text
Tracheostomy:       o2_delivery_device_1 IN ('Tracheostomy tube', 'Trach mask ')
InvasiveVent:       o2_delivery_device_1 IN ('Endotracheal tube')
NonInvasiveVent:    each of slots 1, 2, 3, 4 accepts ('Bipap mask ', 'CPAP mask ')
HFNC:               o2_delivery_device_1 IN ('High flow nasal cannula')
SupplementalOxygen: o2_delivery_device_1 IN
                    ('Non-rebreather', 'Face tent', 'Aerosol-cool',
                     'Venti mask ', 'Medium conc mask ', 'Ultrasonic neb',
                     'Vapomist', 'Oxymizer', 'High flow neb', 'Nasal cannula')
None:               o2_delivery_device_1 IN ('None')
```

Non-zero demo counts in the ranked dependency output were: `Trach mask ` 1;
`Bipap mask ` 8 and `CPAP mask ` 4 in slot 1; `High flow nasal cannula` 41;
`Non-rebreather` 18, `Face tent` 98, `Aerosol-cool` 42, `Venti mask ` 5,
`Medium conc mask ` 8, `High flow neb` 17, `Nasal cannula` 884, and `None` 5.
The other listed device literals and NIV mask slots had zero demo rows. The
resulting CASE counts over the unioned event grid were `Tracheostomy=1`,
`InvasiveVent=1,269`, `NonInvasiveVent=21`, `HFNC=41`,
`SupplementalOxygen=1,072`, `None=5`, and unmatched NULL `546`.

The exact `ventilator_mode` invasive set is:

```text
'(S) CMV', 'APRV', 'APRV/Biphasic+ApnPress', 'APRV/Biphasic+ApnVol',
'APV (cmv)', 'Ambient', 'Apnea Ventilation', 'CMV', 'CMV/ASSIST',
'CMV/ASSIST/AutoFlow', 'CMV/AutoFlow', 'CPAP/PPS', 'CPAP/PSV',
'CPAP/PSV+Apn TCPL', 'CPAP/PSV+ApnPres', 'CPAP/PSV+ApnVol', 'MMV',
'MMV/AutoFlow', 'MMV/PSV', 'MMV/PSV/AutoFlow', 'P-CMV', 'PCV+',
'PCV+/PSV', 'PCV+Assist', 'PRES/AC', 'PRVC/AC', 'PRVC/SIMV', 'PSV/SBT',
'SIMV', 'SIMV/AutoFlow', 'SIMV/PRES', 'SIMV/PSV', 'SIMV/PSV/AutoFlow',
'SIMV/VOL', 'SYNCHRON MASTER', 'SYNCHRON SLAVE', 'VOL/AC'
```

The exact `ventilator_mode_hamilton` invasive set is:

```text
'APRV', 'APV (cmv)', 'Ambient', '(S) CMV', 'P-CMV', 'SIMV',
'APV (simv)', 'P-SIMV', 'VS', 'ASV'
```

The exact Hamilton non-invasive set is `('DuoPaP', 'NIV', 'NIV-ST')`.
Non-zero demo counts in the grouped output were `ventilator_mode`: `APV
(cmv)=1`, `CMV/ASSIST=29`, `CMV/ASSIST/AutoFlow=467`, `CPAP/PPS=1`,
`CPAP/PSV=467`, `CPAP/PSV+ApnPres=1`, `CPAP/PSV+ApnVol=8`, `MMV/PSV=2`,
`MMV/PSV/AutoFlow=21`, `PSV/SBT=27`; and `ventilator_mode_hamilton`:
`APV (cmv)=219`, `P-CMV=15`, `VS=10`, `ASV=1`, `NIV=7`, `NIV-ST=2`.
All other listed literals had zero demo rows; zero is a data count, not a
permission to remove a source literal.

## Final ventilation output provenance

The source columns in the final result map as follows; these are derived
columns, not additional FHIR resource elements:

| Ventilation source/output column | Mapping | FHIR/target type |
|---|---|---|
| `stay_id` | ICU Encounter `{"path": "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", "name": "stay_id_str"}` joined by the dependency's `icu_encounter_key` | FHIR string; final `INTEGER` |
| `starttime` / `endtime` | dependency `charttime`, originally `{"path": "(effective).ofType(dateTime)", "name": "effective_datetime"}` | FHIR dateTime string cast to `TIMESTAMP_NTZ`; final `TIMESTAMP` |
| `ventilation_status` | CASE over published `o2_delivery_device_1`–`_4`, `ventilator_mode`, and `ventilator_mode_hamilton` | derived `VARCHAR` |
| final patient identity key | dependency `patient_key` retained from `subject.getReferenceKey(Patient)` | opaque `STRING`, required `patient_key` |
| final ICU encounter identity key | dependency `icu_encounter_key` retained from `encounter.getReferenceKey(Encounter)` | opaque `STRING`, required `icu_encounter_key` |

The temporal windows, 14-hour segmentation, `UNION DISTINCT`, and final
`HAVING MIN(charttime) != MAX(charttime)` are source SQL semantics. They must
run over the dependency keys and `charttime`; no source `vent_seq` or resource
identifier is recoverable or needed.

## Gaps and essentiality

1. **No current gap for the essential text inputs.** The old numeric-row
   categorical loss is repaired in the rebuilt warehouse. For exactly the
   three ventilator text itemids, direct `valueString` plus matching
   `component.valueString` covered every source text row, and the text pivot
   agreed on 2,742/2,742 groups. No whole-concept blocking recommendation is
   warranted from this field.
2. **No current gap for ICU stay identity.** The Observation reference and ICU
   Encounter identifier were populated on 19,224/19,224 target rows. The
   integer `stay_id` is absent from the dependency's published relation but is
   absent-but-derivable from the ICU Encounter `identifier.value`, not from an
   id algorithm. This is an interface requirement, not a semantic loss.
3. **No current gap for `charttime` in the rebuilt demo.** The dateTime choice
   was populated 19,224/19,224 and matched the DuckDB source wall time on
   19,224/19,224 tuples. The historical DST-gap behavior in the shared notes
   was not observed in this UTC-rebuilt probe. Do not add a UUID side channel
   or a DST correction.
4. **`storetime`/`issued` is an indirect, bounded dependency concern.** The
   source oxygen dependency orders duplicate rows by `storetime`; FHIR carries
   `Observation.issued`, but its native instant read is not always the same
   wall-clock value as the source timestamp. The measured oxygen pivot was
   nevertheless exact on all 1,154 demo groups, and the completed full
   dependency attempt was exact. This can theoretically change a ranked slot
   and is therefore to be checked by the dependency's full comparison, but
   the measured affected output count here is 0/1,154; it does not justify
   blocking ventilation or recovering `storetime` from an opaque id.
5. **Numeric source text is ancillary for oxygen flow.** FHIR does not retain
   the original text when a flow row has a numeric Quantity, but oxygen uses
   resource presence plus Quantity/issued ordering rather than the text value.
   No output-affecting demo loss was observed.

## Notes and provisional fragments

Mapping decisions changed by established `MIMIC_NOTES.md` entries:

- the identifier-spine and opaque-key entries required Patient/ICU Encounter
  `identifier.value` for `subject_id`/`stay_id`, with keys used only for
  equality joins;
- the exact itemid/system and profile entries required the proprietary
  chartevents system plus exact code, never `meta.profile`;
- the categorical-chartevents rebuild entry required the component text
  branch for `223848`, `223849`, and `229314`;
- the polymorphic/effective and UTC-rebuild entries required separate choice
  projections and `TIMESTAMP_NTZ`, with no historical DST workaround;
- the ICU Encounter identifier-system entry required filtering the ICU stream
  by `identifier.system`, not `Encounter.class`.

The following provisional fragments were read and treated as leads: 
`MIMIC_NOTES.d/ventilator_setting.md` and
`MIMIC_NOTES.d/oxygen_delivery.md`. The component-text and repeated-row leads
were verified against the authoritative probe. The provisional claim that
`issued` is directly wall-time-identical to `storetime` was not reproduced;
the bounded result is recorded in this mapping and in the owned fragment
`MIMIC_NOTES.d/ventilation.md`. `MIMIC_NOTES.md` was not edited.

No ViewDefinition or `concept.sql` was authored for ventilation. This file is
the reusable fhir-prober carryover only.
