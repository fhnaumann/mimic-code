## Equivalence judge — `charlson` attempt 0006

Verdict: `accept` for the `contested` review.

All 61 conflicts are wholly inherited from the accepted `age` dependency. `mimic-fhir/sql/fhir_patient.sql:15` computes `Patient.birthDate` from `MIN(transfers.intime) - anchor_age`, and line 108 writes it. Canonical `mimic-iv/concepts/demographics/age.sql:30` requires the original `anchor_age`/`anchor_year` pair. Neither exact input is carried by a Patient element or MIMIC-specific extension; encounter-derived estimates are not exact, and opaque resource IDs cannot recover them. No defensible FHIR query can reconstruct the oracle age.

Attempt 0006 correctly consumes `FROM age`, applies the canonical thresholds and arithmetic, and introduces no Charlson-originated divergence. Of the dependency's 460 age conflicts, exactly 61 cross the 50/60/70/80 thresholds; the remaining 399 stay within-band. Those 61 produce one-point differences in both `age_score` and the index. All 17 comorbidity flags match, with zero only-oracle, only-candidate, or differing-null-only rows.

The affected fraction is 61/431,231 = approximately 0.0141%; total and representable identical fidelity are both 431,170/431,231 (99.9859%). The judge found the inherited upstream transformation acceptable under the contract's explicit birthDate and wholly-inherited-divergence rules. No new dataset-wide quirk was identified; the relevant transformation is already in curated `MIMIC_NOTES.md`.
