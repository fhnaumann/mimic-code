## Diagnosis

**Root cause:** The 61 conflicts are inherited upstream ETL transformation loss from the divergent `age` dependency, not a Charlson port bug.

Attempt 0002 correctly consumes `FROM age` at `concept.sql:130-140` and applies the canonical thresholds exactly. The comparison shows:

- 61 `differing_conflict` rows
- Conflicts only in `age_score` and `charlson_comorbidity_index`
- 0 `only_oracle`, `only_candidate`, or `differing_null_only`
- All identifiers, diagnosis flags, row inclusion, schema, and 431,231-row grain match
- 431,170 rows are identical

The conflict samples consistently show `age_score` one point higher and the index one point higher. This follows directly from the index adding `age_score` once; no diagnosis component differs.

**Exact ETL cause:** `mimic-fhir/sql/fhir_patient.sql:15` synthesizes `Patient.birthDate` as `MIN(transfers.intime) - anchor_age` and writes it to `Patient.birthDate` at line 108. Canonical age requires the original `anchor_age` and `anchor_year` pair. Neither field is preserved in Patient or an extension, and encounter-derived estimates of `anchor_year` are not exact. Consequently, no defensible FHIR query can recover the canonical age for patients whose earliest-transfer year differs from `anchor_year`. Resource/reference IDs are opaque and cannot be used as a recovery side channel.

The 460 known upstream age conflicts collapse to 61 Charlson conflicts because only ages crossing the canonical 50/60/70/80 thresholds alter `age_score`.

**Recommended fix:** None in Charlson. Keep attempt 0002's dependency boundary and `FROM age`; do not rederive age or alter its threshold/index logic. Exact agreement requires an upstream representation change preserving the anchor pair or an equivalent exact value.

**Classification:** **Upstream transformation loss.** No carryover stage is at fault; invalidate neither `source-analyst` nor `fhir-prober`. Do not retry Charlson—route this contested review to the equivalence judge.

**Evidence:** Concept `charlson`, attempt `0002`, tier `contested`. Read `AGENTS.md`, `LOOP_CONTRACT.md`, the `concept-equivalence` skill, canonical `charlson.sql`, both Charlson attempt directories, attempt 0002 SQL and ViewDefinitions, the source/FHIR carryovers, the Charlson oracle-manifest entry, sectioned `comparison.full.json`, `run_meta.full.json`, and `mimic-fhir/sql/fhir_patient.sql`. Checked the established `MIMIC_NOTES.md` entries “Patient.birthDate is NOT anchor_year - anchor_age,” the absence of anchor fields/extensions, and the opaque identifier rule; the birthDate entry explains the divergence. Divergence classes: 61 `differing_conflict`, 0 `only_oracle`, 0 `only_candidate`, and 0 `differing_null_only`. Root cause is the irreversible synthesis at `mimic-fhir/sql/fhir_patient.sql:15`, propagated through `age` into Charlson's threshold score and index. Recommended action is no Charlson SQL change and equivalence-judge review. No notes fragment was read as authority, appended, or modified.
