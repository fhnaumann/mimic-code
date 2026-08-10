## Evidence

The FHIR probe read the source carryover, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the notes protocol, canonical ViewDefinition conventions, and provisional blood-gas mapping as a lead. It probed the authoritative demo Delta with embedded Pathling/Spark, not stale ndjson or an HTTP server.

The mapping uses labevent Observations filtered by `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`, joins specimen references to `Specimen.identifier` with the lab-specimen system, and left-joins patient and hospital Encounter identifier spines. `subject_id`, `hadm_id`, and `specimen_id` are cast from identifier strings to integers; `hadm_id` remains nullable. Item codes are projected under `forEach` over matching codings. `effective.ofType(dateTime)` supplies charttime and is cast to `TIMESTAMP_NTZ`; Quantity value is cast to numeric because its materialized alias is string-like.

The exact 23 source itemids were confirmed in Delta. The demo had 11,908 targeted Observations, 11,865 eligible numeric rows, and 2,763 eligible specimen groups. Patient/specimen references and effective dateTime were populated for all targeted Observations; hospital Encounter references were present for 6,408/11,908. Numeric and identifier pivots agreed 2,763/2,763 with the oracle. One known DST-normalized timestamp differed (source `2116-03-08 02:52`, FHIR `03:52`), consistent with the curated datetime note. No new dataset-wide note was appended.

Reusable mapping was written to `mimic-iv/concepts_fhir/carryover/blood_differential/fhir-prober.md` and recorded with the carryover controller. No ViewDefinition or SQL was authored.
