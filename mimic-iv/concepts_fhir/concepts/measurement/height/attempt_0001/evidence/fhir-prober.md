Evidence block — Concept `height`.

The prober read `AGENTS.md`, `LOOP_CONTRACT.md`, source carryover, curated `MIMIC_NOTES.md`, all existing fragments, the canonical Observation ViewDefinition, and the chartevents ETL. It probed embedded Pathling/Spark over the authoritative demo Delta.

Mapping: chartevents Observations use system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` with codes `226707` (Height, inches) and `226730` (Height (cm)). Subject and ICU stay IDs come from Patient and ICU Encounter identifier values, cast to INTEGER; charttime comes from `effective.ofType(dateTime)` and must be cast to `TIMESTAMP_NTZ`; numeric value comes from `value.ofType(Quantity).value` and requires numeric casting. The final value is `ROUND(quantity * 2.54, 2)` for 226707 and `ROUND(quantity, 2)` for 226730, filtered to `120 < height < 230`.

Checks found 71 rows/resources for each item code, all target fields populated, 142/142 source/FHIR rows aligned, and 69/69 reconstructed filtered tuples exact in demo. No target duplicates or cross-stream stay mismatches occurred. The ETL's DST-gap timestamp normalization remains a possible full-data intrinsic divergence.

Produced/reused analysis: `mimic-iv/concepts_fhir/carryover/height/fhir-prober.md`, recorded in `mimic-iv/concepts_fhir/carryover/height/carryover.json`. Dataset-wide finding appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/height.md`: mixed Pathling alias typing for `Observation.effective[x]`. No ViewDefinitions, concept SQL, or commits were authored.
