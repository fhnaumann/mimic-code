# FHIR-prober evidence

The prober read the source carryover, contract, policy, curated notes, and sibling medication fragments, then independently checked the authoritative Delta with embedded Pathling/Spark. Milrinone is represented by ICU `MedicationAdministration`, filtered by `medication` coding system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu` and code `221986`. The demo target had 15 resources and 15 distinct `(stay_id,starttime)` rows. ICU stay identity is obtained by joining `context.getReferenceKey(Encounter)` to `Encounter.identifier` with system `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`, then casting `identifier.value` to integer.

`rate` and `amount` map to dosage rate/dose Quantity values; aliases are string-like while raw values are decimal(32,6), so final SQL must cast to `FLOAT`. `starttime`/`endtime` map to effective Period start/end, with a dateTime fallback for endtime on rate-null administrations; cast datetimes to `TIMESTAMP_NTZ`. ICU MedicationAdministration has no identifier/linkorderid path, so `linkorderid` must be a typed NULL. Resource ids remain opaque join identity only. Dataset-wide findings were appended to `MIMIC_NOTES.d/milrinone.md`.

Reusable mapping: `mimic-iv/concepts_fhir/carryover/milrinone/fhir-prober.md`. Evidence source: the authoritative local Delta probe and its recorded carryover output.
