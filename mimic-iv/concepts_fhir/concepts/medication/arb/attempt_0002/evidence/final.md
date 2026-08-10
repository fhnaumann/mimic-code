# Final evidence

Concept: `arb`.

Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the equivalence judge. Attempt 0002 is the accepted attempt. Full-data runs consumed: **1 completed** (attempt 0002); attempt 0001's submitted job was cancelled before execution and produced no full-data artifacts.

Full comparison: schema matched; candidate and oracle each had 39,534 rows; the unkeyed full-tuple comparison classified a contested review with 3,182 `only_candidate` NULL-period tuples and 3,182 `only_oracle` timestamp tuples (8.049%). The judge accepted this as intrinsic upstream ETL loss: `mimic-fhir/sql/fhir_medication_request.sql:172-177` omits invalid/incomplete `MedicationRequest.dispenseRequest.validityPeriod`, and no alternate FHIR element preserves the original endpoints. The judge cited `:43-44`, `:55,124`, `medication_prescriptions.sql:19-58`, and `medication_mix.sql:27-53,64-85`.

Artifacts: `comparison.full.json`, `run_meta.full.json`, implementation ViewDefinitions and `concept.sql`, plus all stage evidence under this attempt. `MIMIC_NOTES.md` entries were read and applied; none were added or updated. `divergent_dependencies('arb')` returned `[]`.
