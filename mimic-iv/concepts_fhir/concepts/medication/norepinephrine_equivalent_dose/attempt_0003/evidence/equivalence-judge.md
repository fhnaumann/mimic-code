# Equivalence-judge evidence

- Verdict: `accept` for the `review` result; controller outcome should be `COMPLETED_WITH_DIVERGENCE`.
- Tier/classification: `contested` / `unavailable_no_key`; residual pairing was unanchored and paired zero, so `only_oracle=1,707` and `only_candidate=1,706` cannot be separated by counts.
- Oracle/candidate rows: 619,330 / 619,329; net deficit one row, non-gating. Schema matched. Exact multiset intersection was 617,623 rows (99.72438% of oracle), but this is not row-aligned fidelity evidence.
- Accepted upstream citations: rate is sourced/written at `mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99` and served at six-decimal precision with discarded low-order digits unrecoverable by FHIR; `inputevents.patientweight` is absent from the exhaustive projection/resource construction at `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`, while `mimic-iv/concepts/medication/phenylephrine.sql:5-7` needs it for `mcg/min` normalization.
- The target exactly applies the canonical formula through accepted `vasoactive_agent`; no target bug or forbidden resource-id inference was found. `linkorderid` is not consumed. The UTC rebuild reached this path, so no DST explanation was accepted.
- The one patientweight-dependent missing interval is inherited and does not justify blocking this downstream concept; the dominant six-decimal substitutions are also inherited. No retry is warranted.
- Judge-identified dataset-wide quirk for fragment recording: ICU MedicationAdministration omits `inputevents.patientweight`, leaving weight-normalized `mcg/min` rates unrecoverable. No fragment was cited as evidence.
