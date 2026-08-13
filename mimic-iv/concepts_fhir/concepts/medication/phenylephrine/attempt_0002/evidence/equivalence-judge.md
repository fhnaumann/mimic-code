# Equivalence judge evidence

- Concept: `phenylephrine`; attempt: `0002`.
- Verdict: `accept` for `review` / `contested` / `paired_residual`.
- Oracle and candidate both preserve 193,260 rows and multiplicity. Representable-column fidelity is 191,421/193,260 (99.05%); the all-NULL `linkorderid` declaration explains the 0.00% total identical headline.
- The judge accepted the intrinsic ETL losses: irreversible `TIMESTAMPTZ` normalization at `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`, six-decimal dose Quantity serialization at `:12,85-90`, and omitted `linkorderid`/`patientweight` at `:7-23,38-100`. The surviving `rateuom` discriminator at `:91-98` makes the one `mcg/min` row's typed NULL `vaso_rate` faithful rather than an estimate.
- The residual conflict counts are amplified by unkeyed stay-only pairing and do not establish another mapping defect. Missing fields do not change inclusion, multiplicity, grain, grouping, carry-forward, or other clinically meaningful outputs.
- Exact justification recorded for `accept-divergence`: the port faithfully maps the exact ICU MedicationAdministration code and every available FHIR path; the remaining divergence is intrinsic and ancillary, with the row-level uncomputable rate honestly NULL.
- No new fragment section was needed: the phenylephrine fragment already records the ICU omission and rate-unit discriminator claim. No sibling claim was promoted to curated notes.
