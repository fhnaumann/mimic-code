# FHIR-prober evidence — sapsii attempt_0001

The prober read the source carryover, loop contract, curated `MIMIC_NOTES.md`,
relevant provisional fragments, completed dependency carryovers, the Delta
warehouse, DuckDB demo oracle, and upstream `mimic-fhir` SQL. It mapped the ICU
and hospital Encounter streams, Patient identifiers, CPAP Observation,
hospital-linked Condition diagnoses, and all nine completed derived dependency
relations. It confirmed that resource/reference keys are opaque and must be
joined/emitted unchanged, while numeric identifiers come from the appropriate
`identifier.value` and require integer casts.

Key checks: ICU stay identifier/time/parent/patient mappings agreed 140/140;
hospital admission priority and first-service classification agreed 275/275;
CPAP item `226732` and `(cpap mask|bipap)` text selection agreed 32/32; and
hospital-linked diagnosis tuples agreed 4,506/4,506 using the served
proprietary ICD-9/ICD-10 systems. Dependency joins must use published resource
keys and timestamp windows, and Quantity aliases must be cast before numeric
aggregation. The inherited age derivation's full-data conflict is potentially
score-relevant and is deliberately deferred to the full comparator.

Reusable mapping: `mimic-iv/concepts_fhir/carryover/sapsii/fhir-prober.md`.
The prober appended the dataset-wide served Condition coding-system finding to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/sapsii.md`; curated `MIMIC_NOTES.md` was
not edited. No ViewDefinition or SQL was authored.
