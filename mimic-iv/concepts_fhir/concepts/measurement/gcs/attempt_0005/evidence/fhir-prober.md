# FHIR prober evidence — gcs

The fresh probe wrote
`mimic-iv/concepts_fhir/carryover/gcs/fhir-prober.md` after checking the
authoritative demo Delta with embedded Pathling/Spark, the canonical source
SQL, the chartevents ETL, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, and all notes
fragments.

The three target codes are carried verbatim in the chartevents coding system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`.
Observation references join to Patient and ICU Encounter, whose identifier
values are cast from strings to integer output columns. Effective dateTime is
the direct charttime path and must be parsed as `TIMESTAMP_NTZ`; Quantity value
is the numeric component path.

The exact source label `No Response-ETT` is absent from direct FHIR value
paths: it is conflated with `No Response` as Quantity 1. This changes
`gcs_unable`, verbal score, total GCS, and carry-forward, so it is essential.
Observation/resource IDs are opaque and were not used to recover the label or
pre-normalization time. No new dataset-wide note was appended.

Artifacts: the fresh carryover mapping above; no ViewDefinition or SQL was
created by this stage.
