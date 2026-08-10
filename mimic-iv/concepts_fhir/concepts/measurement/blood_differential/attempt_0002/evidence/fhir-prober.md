## Evidence

The corrected probe read reusable source analysis, attempt 0001 diagnosis, `LOOP_CONTRACT.md`, curated notes, the current provisional fragment, and canonical ViewDefinition conventions. It verified the FHIR representation in demo Delta with embedded Pathling/Spark.

The required correction is to project `Observation.value.ofType(Quantity).comparator` as `quantity_comparator` and accept numeric rows only when the cast Quantity value is non-null, comparator is NULL, and value is non-negative. This preserves source `valuenum IS NOT NULL` semantics: ETL-synthesized `<0.1` rows have value `0.1` with comparator `<` and must be excluded. Quantity value remains string-like and needs a numeric cast; dateTime remains `TIMESTAMP_NTZ`; hadm_id uses a nullable left Encounter identifier join.

The exact code set was reconfirmed. Demo counts remained 11,908 targeted / 11,865 source-eligible, with no comparator rows in the demo; the prior full diagnosis establishes the five comparator-bearing item `51301` rows. The known DST timestamp transformation remains intrinsic. No new notes fragment entry was needed.

Updated reusable mapping: `mimic-iv/concepts_fhir/carryover/blood_differential/fhir-prober.md`, recorded with the carryover controller. No attempt artifact or curated notes file was edited.
