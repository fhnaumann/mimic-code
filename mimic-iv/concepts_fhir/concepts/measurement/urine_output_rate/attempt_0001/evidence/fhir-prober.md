# FHIR-prober evidence — `urine_output_rate`

The prober read the source analysis, canonical SQL, `LOOP_CONTRACT.md`,
`MIMIC_NOTES.md`, and provisional fragments for `urine_output`,
`first_day_urine_output`, and `weight_durations`. It queried the authoritative
demo Delta with embedded Pathling/Spark and checked the relevant ETL SQL.

Direct mappings established:

- ICU `Encounter`, filtered by identifier system
  `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`: `value` is the
  numeric `stay_id` string; `period.start`/`period.end` are ICU times;
  `getResourceKey()` and `subject.getReferenceKey(Patient)` are required opaque
  `icu_encounter_key` and `patient_key` outputs.
- ICU chartevents `Observation`: equality-join
  `encounter.getReferenceKey(Encounter)` to the ICU Encounter resource key;
  `(effective).ofType(dateTime)` is chart time; filter coding system
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` plus
  exact code `220045` (Heart Rate).
- Completed dependencies remain `urine_output` and `weight_durations`; no
  dependency source FHIR resources are rederived.

Probes found 140 ICU Encounters and 13,913 exact-code Observations, with all
target references, keys, codes, and effective dateTimes populated. The
Observation-to-Encounter equality join resolved 13,913/13,913 rows. Effective
time was dateTime-only; two demo source 02:00 DST-gap rows became candidate
03:00 multiplicities. ICU endpoint agreement was 140/140 in demo. The original
wall time is not recoverable from FHIR and resource ids remain opaque.

Reusable mapping facts were written to and recorded from
`mimic-iv/concepts_fhir/carryover/urine_output_rate/fhir-prober.md`. No new
dataset-wide fragment was appended because the observed quirks are already in
`MIMIC_NOTES.md`.
