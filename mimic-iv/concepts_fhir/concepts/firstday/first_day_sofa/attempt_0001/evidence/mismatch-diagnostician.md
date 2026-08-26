# Mismatch diagnostician evidence — `first_day_sofa`

## Diagnosis

- Current full result is a contested review: 22 `differing_conflict` rows, zero row-presence or null-only differences, on `cardiovascular` and `sofa`; 73,159/73,181 rows identical.
- 18 rows are a fixable attempt-scoped Spark type-coercion bug at `concept.sql:135-143`: published FLOAT rates compared with untyped decimal `0.1`, so served `0.10000000149011612` takes the `> 0.1` score-4 branch while the oracle takes score 3. Type the threshold literals as FLOAT while preserving the canonical CASE exactly.
- Four rows are upstream precision loss: source dopamine maxima around `5.000000476837158` are served as six-decimal `5.000000`, collapsing distinct source values. The candidate falls from the canonical `> 5` score-3 branch to score 2. Do not change `> 5` to `>= 5`, add epsilon, or use ids.
- Upstream citation for the residual: `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`, where the rate's only semantic FHIR representation is `dosage.rateQuantity.value` at six-decimal precision. The lost low-order digits are non-injective and unrecoverable by a compliant query; resource identity was not used.
- The four-row residual changes cardiovascular and total SOFA, so the later judge must assess its essentiality after the fixable 18 rows are removed.
- No carryover stage is faulty; no invalidation is needed. No new dataset-wide note was appended because MIMIC_NOTES.md already records six-decimal ICU MedicationAdministration quantities.

## Dependency assessment

The target's current divergent-dependency list is conservative provenance. The diagnosis checked staged dependency artifacts: `bg`, `first_day_lab`, urine-output, ventilation and related transitive paths were exact on rebuilt data; the consumed dopamine/norepinephrine rates expose the threshold/precision issue; historical GCS/vitalsign/BG/urine DST leads do not explain these current rows.

## Evidence block

Read/checks: read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, oracle manifest, canonical SQL, all attempt ViewDefinitions and SQL, `comparison.full.json`, `run_meta.full.json`, state/carryover files, remote dependency manifest, and current direct/transitive dependency comparison artifacts. Performed full-oracle source-side threshold/precision probes and traced all 22 conflicts. Classification: fixable bug plus a separately identified four-row upstream transformation-loss residual. Remedy is a new attempt with FLOAT-typed `0.1` thresholds; no carryover invalidation. No files, state, or notes were edited by the diagnostician and no commit was made.
