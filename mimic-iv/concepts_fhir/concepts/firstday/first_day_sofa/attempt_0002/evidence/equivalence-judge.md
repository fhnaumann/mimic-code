# Equivalence judge evidence — `first_day_sofa` attempt 0002

## Verdict

**Verdict: `blocked`.**

- Tier: `contested`; 24 `differing_conflict` rows on `cardiovascular` and `sofa`; 0 `only_oracle`, 0 `only_candidate`, 0 `differing_null_only`; 73,157/73,181 rows identical (99.9672%).
- Citation: `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`, especially line 94, writes the sole semantic rate representation to `MedicationAdministration.dosage.rateQuantity.value`; curated `MIMIC_NOTES.md:946-958` records six-decimal Quantity precision.
- The loss is non-injective: source rates just above SOFA thresholds 0.1 or 5 collapse to exact served thresholds. Amount/period are not lossless rate encodings, and opaque ids cannot be used.
- Attempt 0002 exhausted the defensible port fix by FLOAT-typing the 0.1 thresholds while preserving the canonical CASE. The residual changes the clinically meaningful cardiovascular component and total SOFA, so it is essential loss rather than an ancillary gap.
- Divergent dependencies (`dobutamine`, `dopamine`, `epinephrine`, `first_day_gcs`, `first_day_vitalsign`, `norepinephrine`) do not explain these target rows; the relevant loss is the consumed medication rate precision.

## Evidence block

Read/checks: judge read `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, both comparisons/runtime artifacts, both attempts’ SQL/ViewDefinitions/evidence, relevant dependency states/mappings, and the cited upstream ETL. It did not read or modify notes fragments and made no file changes or commit. Comparator fidelity and representable fidelity were both 99.9672%; terminal authority is the judge’s `blocked` ruling because the intrinsic precision loss makes the SOFA output unreliable.
