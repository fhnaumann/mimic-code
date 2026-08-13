# Evidence — fhir-prober

The reopened instruction was obeyed: resource/reference IDs remain opaque and
were not parsed, regenerated, hardcoded, or used to infer charttime. The fresh
embedded Pathling/Spark probe mapped chartevents Observations by exact system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and
codes `226707` and `226730`; it mapped numeric subject/stay identifiers through
Patient and ICU Encounter identifier spines. Quantity aliases are strings and
effective dateTime is cast directly to `TIMESTAMP_NTZ`.

The authoritative demo probe found 71 rows per code, 142/142 populated target
fields and successful Patient/ICU Encounter joins. Derived bounded output was
69/69 exact demo tuples. No new dataset-wide quirk was found and no notes
fragment entry was added. The prior full residual of four +1-hour charttime
conflicts is an upstream DST-gap normalization to be handled by the comparator
and judge, not by ID inversion.

Artifact: `mimic-iv/concepts_fhir/carryover/height/fhir-prober.md`.
