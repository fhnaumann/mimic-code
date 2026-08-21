# Evidence: fhir-prober — `kdigo_uo`, attempt 0001

## Sources read

Read the exact source analysis at
`mimic-iv/concepts_fhir/carryover/kdigo_uo/source-analyst.md`, the complete
curated `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, and relevant provisional
fragments `urine_output.md`, `first_day_urine_output.md`, `first_day_weight.md`,
`weight_durations.md`, and `icustay_times.md`. Read the completed dependency
carryovers and attempt-0003 mappings/comparisons for `urine_output` and
`weight_durations`, the canonical observation ViewDefinition, and the
`kdigo_uo` oracle manifest entry. No HTTP Pathling endpoint or NDJSON was used.

## Embedded Pathling/Spark checks

The authoritative demo Delta was probed with embedded Pathling 9.6.0/Spark
4.0.2 at `/Users/nau025/warehouses/mimic-iv-demo/delta`; the read-only DuckDB
oracle was `/Users/nau025/warehouses/mimic4-demo.db`.

- ICU Encounter projection: 140 ICU rows; `icu_encounter_key`, `patient_key`,
  `stay_id_str`, `intime_datetime`, and `outtime_datetime` were each 140/140
  non-null. Resource/reference keys were 140/140 in `Type/id` shape.
- Outputevents target: 7,349 coding rows over 7,349 distinct resources, ratio
  1.000. `observation_key`, `patient_key`, `encounter_key`, item code/system,
  Quantity value/unit, and effective dateTime were all 7,349/7,349 non-null;
  ICU equality join and recovered stay identifier were 7,349/7,349. Period
  start/end and instant variants were each 0/7,349.
- Chartevents weight target: 570 coding rows over 570 distinct resources,
  ratio 1.000. Keys/references, item code/system, Quantity value/unit, and
  effective dateTime were all 570/570; Period start and instant variants were
  0/570. ICU equality join, stay identifier, and both ICU period endpoints were
  570/570.
- Full coding streams were one coding per resource: output `mimic-d-items`
  24,642/24,642 and chartevents `mimic-chartevents-d-items` 668,862/668,862.

## Confirmed dependency code sets

`kdigo_uo` has no direct code filter. Its dependencies were confirmed as:

- `urine_output`: system
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`; codes
  `226559=6685`, `226560=496`, `226561=90`, `226584=0`, `226563=0`,
  `226564=0`, `226565=0`, `226567=15`, `226557=0`, `226558=0`,
  `227488=32`, `227489=31` in both source and FHIR target counts; total
  7,349/7,349.
- `weight_durations`: system
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`;
  `226512=129` and `224639=441` in both source and FHIR target counts; total
  570/570.

System plus exact code is the discriminator, not `meta.profile`. The output
codes all have `d_items.linksto='outputevents'`; the weight codes have
`linksto='chartevents'`. The shared `mimic-d-items` system for outputevents and
datetimeevents is therefore safe here because `d_items.itemid` is a global PK
with one linksto value and the exact item sets are disjoint.

## Oracle agreement and grain

Pandas comparisons against the DuckDB oracle found output event keys and
values exact at 7,349/7,349, grouped urine output keys and sums exact at
7,317/7,317, weight event keys exact at 570/570, and canonical three-place
weight values exact at 570/570. ICU endpoint tuples agreed 140/140. Demo
dependency shapes were 7,317 urine rows and 578 weight intervals; canonical
`kdigo_uo` was 7,317 rows at 7,317 distinct `(stay_id, charttime)` pairs over
137 stays. The half-open weight join matched 7,226 rows, left 91 without a
weight, and had maximum interval multiplicity 1.

## Mapping and gaps

The complete reusable source-column → FHIRPath/dependency mapping, FHIR types,
materialized alias types, required casts, dependency boundaries, output types,
key requirements, and gap assessment is in
`mimic-iv/concepts_fhir/carryover/kdigo_uo/fhir-prober.md`.

The required paths are ICU Encounter `getResourceKey()` and
`subject.getReferenceKey(Patient)`, ICU identifier `value` filtered by the ICU
identifier system, `period.start`, output Observation
`encounter.getReferenceKey(Encounter)`, output Observation
`(effective).ofType(dateTime)`, output/weight coding `code`/`system`/`display`,
and Quantity value/unit aliases. All resource/reference IDs remain opaque and
are used only for equality joins and required key emission.

The only irrecoverable information identified is upstream TIMESTAMPTZ/DST
normalization of output chart times and ICU period start times. It is essential
to the target key and windows, but is the established upstream DST exception;
the dependency full artifacts bound the observed upstream effects to 393
oracle-only, 157 candidate-only, and 232 conflict urine-output groups, and nine
ICU-intime-derived weight interval effects. No id inversion or reconstruction
was attempted. No new dataset-wide quirk was discovered, so
`MIMIC_NOTES.md` was not edited and `MIMIC_NOTES.d/kdigo_uo.md` was not
appended.

## Artifacts

- Reusable mapping:
  `mimic-iv/concepts_fhir/carryover/kdigo_uo/fhir-prober.md`
- Carryover ledger recorded by:
  `uv run mimic_utils carryover-record kdigo_uo --stage fhir-prober`
- This attempt evidence:
  `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/evidence/fhir-prober.md`
