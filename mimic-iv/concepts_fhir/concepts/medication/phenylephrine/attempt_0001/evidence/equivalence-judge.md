Evidence block — phenylephrine equivalence judge

Verdict: `blocked` for intrinsic essential representation loss. The curated notes, canonical SQL, attempt artifacts, comparison, and diagnostician evidence were reviewed. Canonical `mimic-iv/concepts/medication/phenylephrine.sql:5-7` divides `rate` by `patientweight` for `mcg/min` rows to produce clinically meaningful `vaso_rate` in `mcg/kg/min`. The upstream ETL `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100` omits `inputevents.patientweight` and writes only raw rate/unit to dosage at `:91-98`; no FHIR path carries the exact denominator. Joining unrelated weight Observations would be heuristic, and resource-id inversion is forbidden. The candidate's raw-rate projection is therefore not a faithful mapping for that branch.

Missing `linkorderid`, scale-six Quantity precision, and the rare DST-normalized timestamp are intrinsic but ancillary. The large conflict counts are not reliable event-level fidelity measures because the unkeyed comparator paired repeated administrations only on `stay_id`; nevertheless, the essential patientweight loss independently requires whole-concept `BLOCKED_REPRESENTATION` under the loop contract.

Exact block reason: `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100` omits `inputevents.patientweight` while canonical phenylephrine requires `rate / patientweight` for `mcg/min` administrations; no FHIR path identifies the exact denominator, so the clinically meaningful canonical output is unrecoverable.

Artifacts read: `comparison.full.json`, canonical SQL, `concept.sql`, ViewDefinitions, `unrepresentable.json`, curated `MIMIC_NOTES.md`, and diagnostician evidence. No attempt artifact was modified and no commit was made.
