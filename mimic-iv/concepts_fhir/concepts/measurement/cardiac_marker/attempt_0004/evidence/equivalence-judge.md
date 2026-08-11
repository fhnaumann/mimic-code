# Evidence: equivalence-judge

Concept: `cardiac_marker`; attempt `0004`.

The judge returned `accept` for the `contested` review. The 18 conflicts are
keyed `charttime` differences only; all are candidate 03:xx versus oracle
02:xx, with 295,228/295,246 rows otherwise identical and no row-only or
null-only divergences. There are no divergent dependencies.

The accepted citation is `mimic-fhir/sql/fhir_observation_labevents.sql:15`
(source `lab.charttime` cast through `TIMESTAMPTZ`) and `:121` (written to
`Observation.effectiveDateTime`), with the analogous specimen transform at
`fhir_specimen_lab.sql:9,18,58`. `Observation.issued` is transformed
`storetime`, not original charttime (`fhir_observation_labevents.sql:16,122`).
The spring-forward conversion is non-injective: shifted 02:xx and genuine
03:xx values are indistinguishable in FHIR, so no query can recover the oracle
value without corrupting genuine rows. The current port's
`TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)` faithfully preserves the FHIR
value and removes the prior timezone-sensitive fallback.

Result: `accept`; no new dataset-wide quirk was found and no notes fragment was
appended.
