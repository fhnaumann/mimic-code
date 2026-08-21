# Concept implementer evidence

The implementer read both reusable analyses, the curated notes and fragments,
and the completed `vasoactive_agent` attempt. This concept is dependency-only:
no direct FHIR ViewDefinition is needed. The authored SQL consumes the
published dependency view as `vasoactive_agent`, preserves duplicate rows,
applies the exact five-column non-NULL disjunction, and computes the canonical
formula with a `DECIMAL(38,9)` intermediate and four-place rounding.

The output explicitly casts `stay_id` to `INTEGER`, interval endpoints to
`TIMESTAMP_NTZ`, and the dose to `DECIMAL(38,4)`, while preserving the required
opaque `icu_encounter_key` and `patient_key` verbatim. No patientweight
estimate, resource-id inversion, or unrepresentable declaration was used.

`uv run mimic_utils lint-sql norepinephrine_equivalent_dose` completed cleanly.
No new dataset-wide note was appended.

Artifact: `mimic-iv/concepts_fhir/concepts/medication/norepinephrine_equivalent_dose/attempt_0001/concept.sql`.
