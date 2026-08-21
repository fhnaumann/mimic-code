# FHIR prober evidence

## Evidence — `vasoactive_agent`, attempt_0001

**Resource mappings**

- `mimiciv_icu.inputevents` → `MedicationAdministration`
- `mimiciv_icu.icustays` → ICU `Encounter` support
- `mimiciv_hosp.patients` → `Patient` support
- Parent concept is an interval overlay over the seven dependency views; no standalone FHIR resource represents it.

**MedicationAdministration mappings**

- `{path: "getResourceKey()", name: "medadmin_key"}` — resource-key `VARCHAR`, opaque.
- `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` — reference-key `VARCHAR`.
- `{path: "context.getReferenceKey(Encounter)", name: "encounter_key"}` — reference-key `VARCHAR`.
- `{path: "(effective).ofType(dateTime)", name: "effective_datetime"}` — FHIR `dateTime`, materialized `VARCHAR`.
- `{path: "(effective).ofType(Period).start", name: "effective_period_start"}` — FHIR `dateTime`, materialized `VARCHAR`.
- `{path: "(effective).ofType(Period).end", name: "effective_period_end"}` — FHIR `dateTime`, materialized `VARCHAR`.
- `{path: "(dosage.rate).ofType(Quantity).value", name: "rate_value"}` — FHIR decimal; raw Delta `decimal(32,6)`, materialized `VARCHAR`.
- `{path: "(dosage.rate).ofType(Quantity).unit", name: "rate_unit"}` — `VARCHAR`.
- `{path: "(dosage.rate).ofType(Quantity).system", name: "rate_system"}` — `VARCHAR`.
- `{path: "(dosage.rate).ofType(Quantity).code", name: "rate_code"}` — `VARCHAR`.
- `{path: "(dosage.dose).ofType(Quantity).value", name: "amount_value"}` — FHIR decimal; raw Delta `decimal(32,6)`, materialized `VARCHAR`.
- `{path: "(dosage.dose).ofType(Quantity).unit", name: "amount_unit"}` — `VARCHAR`.
- `{path: "(dosage.dose).ofType(Quantity).system", name: "amount_system"}` — `VARCHAR`.
- `{path: "(dosage.dose).ofType(Quantity).code", name: "amount_code"}` — `VARCHAR`.
- `{path: "identifier.value", name: "identifier_value"}` — `VARCHAR`, 0/1,750 populated.
- `{path: "supportingInformation.reference", name: "supporting_reference"}` — `VARCHAR`, 0/1,750 populated.

Coding projection:

- `{path: "code", name: "item_code"}`
- `{path: "system", name: "code_system"}`
- `{path: "display", name: "code_display"}`

Confirmed system: `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`.

Per-code rows/resources and coding ratio:

- 221653: 44/44
- 221662: 28/28
- 221289: 36/36
- 221906: 947/947
- 221749: 625/625
- 222315: 55/55
- 221986: 15/15

Total: 1,750 rows/resources; ratio `1.000`. Complete coding systems were 34,205 formulary, 20,404 ICU, 1,624 medication-name, and 302 POE-IV rows, each with ratio `1.000`. `CodeSystem` resources are absent.

**Encounter and Patient mappings**

- `{path: "getResourceKey()", name: "encounter_key"}` — ICU Encounter key `VARCHAR`, published as `icu_encounter_key`.
- `{path: "subject.getReferenceKey(Patient)", name: "patient_key"}` — `VARCHAR`.
- `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value", name: "stay_id_str"}` — identifier `VARCHAR`, cast to final `stay_id INTEGER`.
- `{path: "getResourceKey()", name: "patient_key"}` — Patient key `VARCHAR`.
- `{path: "identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value", name: "subject_id_str"}` — identifier `VARCHAR`.

Delta counts: 637 Encounters total, 140 ICU identifiers, all 140 populated; all 1,750 medication references resolved to ICU Encounter identifiers. There were 100 Patients, all with identifiers; subject agreement with DuckDB was 1,750/1,750.

**Effective and oracle checks**

- ICU stream: 20,404 resources; `effectiveDateTime` 9,366, `effectivePeriod` 11,038, dose 20,404, rate 11,038.
- Vasoactive target: Period start/end 1,750/1,750; dateTime 0/1,750.
- DuckDB source: 1,750 rows; all selected fields non-null per itemid.
- Source/FHIR coordinate join: 1,750/1,750, no duplicates or unmatched rows.
- Subject agreement: 1,750/1,750.
- Rate within `1e-6`: 1,750/1,750.
- Amount within `1e-6`: 1,750/1,750.
- Direct units agreed: 1,750/1,750.
- `rateuom` branches requiring patientweight were unexercised in demo: norepinephrine `mg/kg/min` 0/947; phenylephrine `mcg/min` 0/625.

**Gaps**

- `linkorderid`: not representable; ancillary to the parent because it is not consumed. Emit typed NULL in child dependency outputs. Resource IDs remain opaque.
- `patientweight`: not representable. Demo affects 0 rows because both relevant CASE branches are absent. If present in full data, use the surviving `rate_unit` discriminator and emit typed NULL only on affected rate values.
- Rate-null `starttime`: absent from FHIR; 0/1,750 demo rows. It can be essential to the parent interval boundary construction if present in full data.
- Quantity low-order precision: not exactly recoverable; direct FHIR values were within tolerance for all 1,750 rows.
- DST-gap datetime normalization: existing curated note applies; no demo disagreement observed.

**Files**

- Mapping written to `mimic-iv/concepts_fhir/carryover/vasoactive_agent/fhir-prober.md`.
- Recorded with `uv run mimic_utils carryover-record vasoactive_agent --stage fhir-prober`.
- New dataset-wide entries appended only to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/vasoactive_agent.md`: absent `patientweight`, unit trimming, one coding per MedicationAdministration, and absent CodeSystem resources.
- `MIMIC_NOTES.md` was unchanged.
- Read and independently verified provisional fragments: `README.md`, `dobutamine.md`, `dopamine.md`, `epinephrine.md`, `milrinone.md`, `norepinephrine.md`, `phenylephrine.md`, `vasopressin.md`, `neuroblock.md`, and `arb.md`.
