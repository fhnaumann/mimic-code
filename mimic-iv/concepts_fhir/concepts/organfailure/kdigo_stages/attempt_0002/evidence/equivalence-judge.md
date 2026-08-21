# Equivalence judge — `kdigo_stages` attempt `0002`

## Verdict

**accept**. The full-data result is `review`, tier `contested`, classification
`unavailable_no_key`. The unkeyed comparator reported 1,703 `only_oracle` and
1,460 `only_candidate` tuples (oracle 4,011,255; candidate 4,011,012), with no
keyed fidelity fraction. The judge did not treat residual count equality as
evidence; it relied on the full-source replay and the cited upstream ETL.

## Ruling

The diagnosis established 574 DST-shifted timing inputs: 145 from
`kdigo_creatinine`, 393 `kdigo_uo` groups from 395 outputevents rows, 26
retained CRRT times, and 10 ICU `intime` values. Through `UNION DISTINCT`,
exact-time joins, stage calculations, and six-hour smoothing, they explain
1,697/1,703 oracle-only and 1,454/1,460 candidate-only tuples. The remaining
six tuples per side differ only by `0.49999999999999994` versus `0.5`, within
comparator tolerance, leaving semantic residual 0/0. The prior non-DST
`kdigo_uo` precision defect was fixed: four changed output tuples now equal the
oracle.

Confirmed ETL citations and affected FHIR paths:

- `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` →
  `Observation.effectiveDateTime`;
- `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` →
  `Specimen.collection.collectedDateTime`;
- `mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65` →
  `Observation.effectiveDateTime`;
- `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` →
  `Observation.effectiveDateTime`;
- `mimic-fhir/sql/fhir_encounter_icu.sql:31,98` →
  `Encounter.period.start`.

These statements normalize spring-forward-gap source 02:xx wall times to
03:xx and retain no independent pre-normalization witness. Quantities,
store-times, and identifiers do not recover the original chart time; resource
ids remain opaque and cannot be inverted. The target correctly consumes the
published divergent dependencies `crrt` attempt 0007, `kdigo_creatinine`
attempt 0002, and `kdigo_uo` attempt 0004. They account for 564 shifted inputs;
10 shifted ICU admission times are direct. No additional target semantic loss
or essential non-DST residual remains.

The divergence changes event rows, stages, and smoothing, but it is exclusively
proven DST normalization and second-order effects, which the loop contract
requires accepting rather than blocking. Auxiliary exact multiset overlap is
4,009,552/4,011,255 (99.957544%), or 4,009,558/4,011,255 (99.957694%) after
the six within-tolerance pairs; these are not keyed fidelity claims.

## Evidence block

Read and checked the current and prior comparison artifacts, current SQL and
ViewDefinitions, canonical SQL, diagnostician evidence, dependency attempts and
accepted verdicts, `LOOP_CONTRACT.md`, and curated `MIMIC_NOTES.md`. The judge
returned `accept`; no provisional fragment was used and no new dataset-wide
quirk was found. This evidence file was stored by the orchestrator because the
judge is read-only.
