Evidence block — fhir-prober

Read `carryover/first_day_bg/source-analyst.md`, the completed `bg` dependency carryover and attempt `attempt_0006`, `MIMIC_NOTES.md`, provisional lab/time fragments, and the canonical ViewDefinition reference. Used embedded Pathling 9.6.0 / Spark 4.0.2 over `/Users/nau025/warehouses/mimic-iv-demo/delta`; no HTTP server or ndjson.

Probed 637 Encounters (275 hospital, 140 ICU, 222 ED), 100 Patients, and the completed `bg` dependency view (889 rows, `charttime TIMESTAMP_NTZ`, `aado2_calc DECIMAL(38,4)`). ICU Encounter projection was complete (140/140 keys, stay identifiers, patient references, and period starts), with distinct stay IDs. Mapped ICU stays using `identifier.system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'`; `stay_id` from identifier `value`, `subject_id` by opaque reference equality to Patient then the patient identifier value, and `intime` from `period.start`, cast to `TIMESTAMP_NTZ`. The consumer uses the dependency's `subject_id`, `charttime`, and 21 aggregate measurement fields; no re-derivation or consumer code filter is needed.

Verified the inclusive `charttime >= intime - 6 HOURS AND charttime <= intime + 1 DAY` window: 1,577 same-subject pairs before time filtering and 434 inclusive matches (zero observed boundary rows), contributing to 95 stays; the left join retained all 140 ICU stays. The projected output shape was 140 rows and 44 columns, with 140 distinct `stay_id` values; aggregate types were `DOUBLE` except `aado2_calc_min/max` `DECIMAL(38,4)`. DuckDB checks matched ICU spine and all 44 aggregate columns 140/140 on demo.

The inherited `bg` itemids were confirmed on the lab system and chart system, with coding/resource ratio 1.000. The source consumer has no literal code set. No used source field was absent; unused dependency fields are not gaps. Known DST-gap normalization can affect `Encounter.period.start` upstream, but no affected demo ICU starts were observed and no whole-concept block was recommended. Resource/reference IDs were used only for equality joins.

No new dataset-wide quirk was established; no `MIMIC_NOTES.d/first_day_bg.md` fragment was appended.

Artifacts produced:
- `mimic-iv/concepts_fhir/carryover/first_day_bg/fhir-prober.md`
- `mimic-iv/concepts_fhir/carryover/first_day_bg/carryover.json`

No attempt implementation artifacts or commit were made.
