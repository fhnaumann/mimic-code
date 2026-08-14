# Evidence — fhir-prober

Concept `nsaid`, attempt `0001`.

Read the source analysis, canonical SQL, curated notes, all existing fragments,
FHIR mapping conventions, and prescription/mix/MedicationRequest ETL SQL.
Probed the authoritative demo Delta with embedded Pathling/Spark. Confirmed
pharmacy-backed MedicationRequest, direct Medication and repeated mix ingredient
branches, exact medication-name identifiers, Patient/Encounter identifier
joins, and nullable validity-period paths. The demo source/FHIR cohort agreed
on 202 rows and valid endpoint values agreed on 192/192; reversed intervals lose
both endpoints. Resource IDs remain opaque and were not used for recovery.

Artifact produced: `mimic-iv/concepts_fhir/carryover/nsaid/fhir-prober.md`,
recorded in `carryover/nsaid/carryover.json`. No new dataset-wide note was
appended.
