## ICU MedicationAdministration has no independently serialized inputevent orderid
- Affected: `MedicationAdministration.identifier`, `MedicationAdministration.request`, and source `mimiciv_icu.inputevents.orderid`
- Verified: neuroblock embedded Pathling/Spark probe over the authoritative Delta counted 0/20,404 ICU MedicationAdministration resources with a non-empty identifier, 0/20,404 with request, and 0/20,404 with request.identifier.value; `mimic-fhir/sql/fhir_medication_administration_icu.sql:20,40-60` uses orderid only in the opaque resource UUID and writes no inputevent identifier.

## ICU MedicationAdministration medication coding is one coding per resource
- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`
- Verified: neuroblock embedded Pathling/Spark projection over the authoritative Delta counted 20,404 coding rows for 20,404 distinct resources under `mimic-medication-icu` (ratio 1.000), with one coding per resource across all 56,535 MedicationAdministration resources.

## ICU inputevent effective[x] and Quantity branches are encoded conditionally
- Affected: `MedicationAdministration.effective[x]`, `dosage.rateQuantity.value`, and `dosage.dose.value`
- Verified: neuroblock embedded Pathling/Spark schema/count probe over the authoritative Delta found 11,038/20,404 ICU resources with Period start/end and rate Quantity, 9,366/20,404 with dateTime, and 20,404/20,404 with dose Quantity; raw dose/rate values are `decimal(32,6)`. The local ETL writes Period from source start/end when rate is non-null and dateTime from source endtime otherwise (`fhir_medication_administration_icu.sql:61-99`).

## neuroblock row identity survives the loss of orderid
- Affected: `mimiciv_icu.inputevents.orderid`; oracle manifest key `["orderid"]`
- Verified: measured on the full oracle (`mimic-iv/concepts_fhir/oracle/probe_representable_keys.sql`, 2026-08-13) over 14,174 rows: `count(DISTINCT (stay_id, starttime))` = 14,173 — exactly one colliding pair — and `count(DISTINCT (stay_id, starttime, endtime))` = 14,174. `endtime` is representable (it maps from `MedicationAdministration.effective.ofType(Period).end`, coalesced with `effective.ofType(dateTime)`), so **a unique key over columns MIMIC-on-FHIR carries does exist**. The absent `orderid` is therefore surplus to row identity, not the concept's grain.
- Why the manifest keys on `orderid` anyway: `oracle_manifest.py` searches size-first through a fixed identity/time vocabulary, so the one-column `orderid` won at `key_probes: 2` and no two- or three-column candidate was ever probed. The same run measured `dopamine`, `dobutamine`, `vasopressin` and `milrinone` at `(stay_id, starttime)` unique — they carry the identical ETL gap and were judge-accepted. `orderid` is an administrative order number, not clinical identity.
- Do not reason from attempt_0001's counts: it was blocked partly on "28,348 only_oracle" against 14,174 oracle rows, an arithmetic impossibility produced by the anchor-column bug in `compare_port_results.py` (presence was tested as `c.<first key column> IS NULL`, which is also true of every candidate row whose typed-NULL key column is absent). Fixed; the correct figure is 14,174 a side.
- Still expect a `VOID DIFF`: the comparator keys on the manifest key and does not re-key, so attempt 2 will again align zero rows and report no measured fidelity. The acceptance argument rests on the ETL citation plus the grain measurement above, not on an identity fraction.
