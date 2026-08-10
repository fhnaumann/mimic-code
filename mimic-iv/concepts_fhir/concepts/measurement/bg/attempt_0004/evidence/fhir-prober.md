# Evidence: fhir-prober (`bg`, attempt_0004)

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`,
`mimic-iv/concepts/measurement/bg.sql`, and the existing bg source-analysis and
FHIR-prober carryover files.  Probed the authoritative demo Delta warehouse
with embedded Pathling 9.6.0 on Spark 4.0.2; no HTTP Pathling server was used.

Confirmed that lab blood-gas Observations use the
`mimic-d-labitems` code-system binding and ICU chart enrichments use
`mimic-chartevents-d-items`.  The probe found 8,706 targeted lab rows and
15,286 targeted chart rows.  Patient, Specimen, and Observation code/value/
effective mappings were validated against DuckDB; specimen grouping is via
the Observation-to-Specimen reference and lab Encounter enrichment remains a
left join because only 8,024/8,706 lab rows have an Encounter reference.

The reusable mapping confirms identifier values are strings requiring final
INTEGER casts, dateTime values require `TIMESTAMP_NTZ`, Quantity values are
materialized as string-like ViewDefinition aliases requiring numeric casts,
and itemids remain literal proprietary MIMIC codes.  Code `52033` remains
`NULLIF(value_string, '___')` because the upstream comments fallback is not
provenance-preserving.  Two demo DST-gap effective-time collisions were
observed and treated as an upstream transformation, not a port filter issue.

Updated mutable artifacts:

- `mimic-iv/concepts_fhir/carryover/bg/fhir-prober.md`
- `mimic-iv/concepts_fhir/carryover/bg/carryover.json`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md` (added the Quantity.value materialization
  quirk and sharpened the existing DST-gap entry for Observation.effective[x])

No ViewDefinition or `concept.sql` was authored, and no prior immutable
attempt artifact was modified.  The next loop phase is the bg implementer.
