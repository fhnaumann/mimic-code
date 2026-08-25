Evidence block from fhir-prober:

- `mimiciv_icu.chartevents` → FHIR `Observation`.
- Patient identity → `{ "path": "subject.getReferenceKey(Patient)", "name": "patient_key" }` plus Patient identifier path for `subject_id_str`.
- ICU stay identity → `{ "path": "encounter.getReferenceKey(Encounter)", "name": "icu_encounter_key" }` plus ICU Encounter identifier path for `stay_id_str`.
- `chartevents.charttime` → `{ "path": "(effective).ofType(dateTime)", "name": "effective_datetime" }`; materialized `STRING`, cast to `TIMESTAMP_NTZ`.
- `valuenum` → Quantity value path, materialized `STRING`, cast numeric; categorical value → `value.ofType(string)`.
- Numeric-row ventilator text → `value.ofType(string)` under `forEachOrNull: "component"`, with component code/system paths.
- Item coding uses `code`, `system`, and `display` under constrained `code.coding`; `issued` is the storetime ranking input; resource identity is opaque only.

Confirmed system: `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.

Confirmed codes and source/FHIR row counts, all coding/resource ratio `1.000`: `220339=1447, 223834=1090, 223835=1746, 223848=1292, 223849=1048, 224684=769, 224685=1331, 224686=661, 224687=1359, 224688=801, 224689=1314, 224690=1331, 224691=330, 224696=510, 224700=490, 226732=3145, 227287=145, 227582=13, 229314=402`; total `19,224/19,224`. Component text: `223848=906`, `223849=1011`, `229314=402`. Repeated cardinality: item `226732` had 3,145 resources, 3,014 time groups, 106 repeated groups, maximum 3.

Dependency interfaces are published with `patient_key`, `icu_encounter_key`, `charttime`, dependency outputs, and no `subject_id`/`stay_id` after identifier stripping. Dependency replay matched oxygen delivery `1,154/1,154` demo groups and ventilator setting `2,064/2,064` groups; existing full comparisons were exact.

Gaps: ICU `stay_id` is absent from the published dependency relation but exactly derivable through the ICU Encounter identifier. Rebuilt effective datetimes and ventilator component text had no observed loss. `issued` is not always wall-clock-identical to source `storetime`, but oxygen ranking still reproduced `1,154/1,154` demo groups.

Read `MIMIC_NOTES.md`, `ventilator_setting.md`, and `oxygen_delivery.md`; provisional fragment claims were treated as leads. No ViewDefinition or `concept.sql` was authored. Findings were written to `mimic-iv/concepts_fhir/carryover/ventilation/fhir-prober.md` and recorded in the carryover ledger.
