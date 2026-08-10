## FHIR-prober evidence

I read `AGENTS.md`, the FHIR mapping guidance, the source SQL and source carryover, `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, `MIMIC_NOTES.d/README.md`, and the available notes fragments. I probed the authoritative demo Delta with embedded Pathling/Spark and checked the DuckDB demo oracle.

The mapping is `labevents` to lab `Observation`, with `Observation.code.coding.system = http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems` and exact string codes `51003`, `50911`, and `50963`. The numeric value is `(value).ofType(Quantity).value`; `specimen`, `subject`, and hospital `encounter` reference keys join to `Specimen`, `Patient`, and hospital `Encounter` identifier values. Identifier values are strings and must be cast to integer outputs; resource keys are UUIDs and are join-only. Effective dateTime must be cast to `TIMESTAMP_NTZ`. The specimen join is complete, while the hospital encounter join is a LEFT JOIN because 104/386 numeric observations have null encounter/hadm on both sides.

Probe evidence: 541 coded observations (278/187/76 by active code), 386 numeric rows, 283 specimen groups. Numeric values, subject IDs, hadm IDs including nulls, and pivoted analytes agreed with the demo oracle; two source charttimes are irreversibly shifted by the established DST-gap ETL transform. Non-numeric FHIR observations are excluded to preserve the source `valuenum IS NOT NULL` filter.

The concept mapping was written to and recorded at `mimic-iv/concepts_fhir/carryover/cardiac_marker/fhir-prober.md` and its ledger. The prober appended the dataset-wide string-code filtering finding to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/cardiac_marker.md`; `MIMIC_NOTES.md` was not edited. No implementation artifacts were authored.
