# Mismatch diagnostician evidence

- Concept: `phenylephrine`
- Attempt: `0003`
- Read: the full comparison and run metadata, current ViewDefinitions/SQL, canonical source SQL, curated `MIMIC_NOTES.md`, and the ICU MedicationAdministration ETL.
- Diagnosis: no fixable port bug remains. The residual `contested` conflicts are pairing amplification in the unkeyed full-tuple comparison anchored on `stay_id`, caused by upstream precision and timestamp transformations rather than incorrect FHIR paths or SQL.
- Residuals: `starttime` 1,792 after the 29 directly attributed DST conflicts; `endtime` 1,792 after 28 attributed; `vaso_amount` 1,748 overlapping the timing residuals; no `vaso_rate` value conflict, with one intentional row-level NULL.
- Upstream citations: `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69` casts effective endpoints through `TIMESTAMPTZ` and writes the transformed values; `:12,85-90` and `:14,91-99` write six-decimal Quantity values. The source wall time and discarded low-order numeric precision are not present in any FHIR element and cannot be recovered by query. The comparator already machine-attributed 46 DST rows; source replay aligned all remaining endpoint groups and showed representable values within tolerance.
- Representability: `linkorderid` is correctly declared and typed-NULL because the ETL omits it (`:7-23,38-100`) and resource identity is opaque. The one `mcg/min` `vaso_rate` NULL is correct because `rate_unit` survives while `patientweight` does not. Rate-null `starttime` loss is not exercised in the selected full source. These losses are ancillary; the proven DST loss is explicitly not essential-loss blocking under the contract.
- Result: route directly to the equivalence judge; do not invalidate carryover and do not retry.
- Dataset-wide notes: no new quirk appended; existing curated notes already cover ICU medication omissions, Quantity precision, and datetime normalization.
