# Mismatch diagnostician evidence — charlson attempt 0004

The diagnostician classified the 61 conflicts as wholly inherited upstream transformation loss from the completed divergent `age` dependency, not a Charlson port bug. The candidate reads `FROM age` at `concept.sql:141` and uses the canonical age thresholds and Charlson arithmetic (`concept.sql:131-142,167-176`; canonical `charlson.sql:349-358,384-394`). All 17 diagnosis flags, identifiers, row inclusion, grouping, and schema match; only `age_score` and the composite index differ on the same 61 rows, both candidate values exactly one higher in the samples.

The cited upstream cause is `mimic-fhir/sql/fhir_patient.sql:15,108`, which synthesizes `Patient.birthDate` from `MIN(transfers.intime) - anchor_age`. Canonical `age` requires the original `anchor_age`/`anchor_year` pair, neither of which is carried as an exact FHIR field. No defensible query can recover the oracle age for the affected patients, and opaque resource identifiers cannot be used as a semantic side channel. The dependency has 460 age conflicts; Charlson exposes only the 61 threshold crossings at 50/60/70/80. The dependency's separate 44 DST admission-time conflicts do not propagate into Charlson's age values. The loss affects clinically meaningful outputs but is inherited and falls under the accepted upstream birthDate transformation provision, so no retry or carryover invalidation is needed.

Evidence read included the comparison, candidate and canonical SQL, both Charlson carryovers, Charlson attempts, age dependency artifacts/state, `MIMIC_NOTES.md`, `LOOP_CONTRACT.md`, and the cited mimic-fhir ETL. The provisional `MIMIC_NOTES.d/charlson.md` lead was not cited as evidence. No notes fragment was appended and no files were modified.

Artifacts/read paths:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/concept.sql`
- `mimic-iv/concepts_fhir/concepts_fhir/carryover/charlson/` (mapping/source carryover)
- `mimic-iv/concepts_fhir/state/age/state.json`
- `mimic-fhir/sql/fhir_patient.sql`
