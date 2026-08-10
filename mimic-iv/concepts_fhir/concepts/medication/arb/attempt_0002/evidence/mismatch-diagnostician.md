# Mismatch diagnostician evidence

The attempt 0002 full result is a contested `review`, not a machine mismatch. It is unkeyed, with 3,182 candidate-only NULL-period tuples and 3,182 oracle-only tuples; these are paired substitutions of the same prescriptions, not independently invented/missing rows. Schemas and row count (39,534) match.

The port is not fixable. The source emits original endpoints at `mimic-iv/concepts/medication/arb.sql:23-24`. Upstream MIMIC-on-FHIR obtains them at `/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_request.sql:43-44`, but writes `dispenseRequest.validityPeriod` only when start is present and no later than stop at `:172-177`; reversed or incomplete intervals become absent, so both candidate endpoints are NULL. `authoredOn` is pharmacy entry time, not a validity endpoint (`:55,124`), and medication/mix resources preserve names but not prescription times (`medication_prescriptions.sql:19-58`, `medication_mix.sql:27-53,64-85`). The source timestamps are therefore unrecoverable by any FHIR query; estimating them would manufacture conflicts.

The direct and mix branches, multiplicity, exact filters, identifier joins, and timestamp parsing are correct. No carryover invalidation or retry is warranted. Existing `MIMIC_NOTES.md` entry “MedicationRequest omits invalid or incomplete prescription validity periods” already records this dataset-wide quirk; no note was added or changed.

Recommendation: send this contested review to the equivalence judge with the ETL citation. Artifacts reviewed include `comparison.full.json`, `run_meta.full.json`, attempt 0002 implementation files, source SQL, carryover analyses, and the existing medication evidence.
