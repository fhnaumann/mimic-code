# Mismatch diagnostician evidence — `first_day_sofa` attempt 0002

## Diagnosis

- Attempt 0002's FLOAT threshold cast worked as written; it removed the prior 18 upward coercion errors but exposed the other side of the same six-decimal rate collapse.
- Current divergence is 24 `differing_conflict` rows, all on `cardiovascular` and `sofa`; zero row-presence or null-only differences; 73,157/73,181 rows identical.
- Twenty stays have source norepinephrine maxima slightly above `0.1` but served `0.100000`, so the current candidate correctly treats the served value as `<= 0.1` while the oracle takes score 4. Four stays have source dopamine maxima `5.0000004768371582` but served `5.000000`, so the candidate takes score 2 while the oracle takes score 3. Stay `32582168` crosses both thresholds but is counted once.
- The sole semantic rate path is `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`, especially `:94`, where `ie.rate` is serialized as `dosage.rateQuantity.value` at six-decimal scale. Distinct source values collapse to the same served value and no alternate FHIR element preserves the discarded low-order digits. Amount/period are not a lossless rate encoding; resource identity is opaque and was not used.
- All 24 residuals are upstream transformation loss, not a current port bug. No SQL change, carryover invalidation, or retry is warranted. Preserve the four `CAST(0.1 AS FLOAT)` thresholds, canonical OR order, and dopamine `> 5`.
- The lost side-of-threshold information changes the clinically meaningful cardiovascular component and total SOFA; the equivalence judge must decide essentiality and terminal disposition. The diagnostician recommends whole-concept blocking, but this is not a terminal decision by the diagnostician.

## Evidence block

Read/checks: read `AGENTS.md`, `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, canonical SQL, manifest, both carryover files, both attempt SQL/ViewDefinitions/evidence, both full comparisons and runtime/HPC artifacts, dependency manifests and current direct/transitive dependency evidence, and `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql`. Successful full-oracle threshold/precision probes localized all 24 current rows to medication maxima and excluded BG, lab, urine, GCS, ventilation, and rebuilt-DST leads. No resource id was inspected for semantic recovery. No new dataset-wide quirk was established; curated notes already record six-decimal ICU MedicationAdministration precision. No files, state, artifacts, or commits were modified.
