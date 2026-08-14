# FHIR prober evidence

Concept: `urine_output`.

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, canonical observation ViewDefinition, source-analyst carryover, and relevant provisional leads. Probed authoritative demo Delta with embedded Pathling/Spark and checked DuckDB oracle plus local ETL SQL.

## Mappings

- `mimiciv_icu.outputevents` maps to FHIR `Observation`.
- `outputevents.stay_id` maps through `Observation.encounter.getReferenceKey(Encounter)` to ICU `Encounter.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu').value`; the final SQL must cast the identifier string to `INTEGER`.
- `charttime` maps to `(effective).ofType(dateTime)`, materialized as a string; cast to `TIMESTAMP_NTZ`.
- `itemid` maps through `code.coding.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items')`, projecting `code`, `system`, and `display`; cast code to `INTEGER` only after filtering.
- `value` maps to `(value).ofType(Quantity).value`, materialized as a string; cast to `DOUBLE`. Optional unit is `(value).ofType(Quantity).unit`, and target rows were `ml`.

Effective variants: `effective_datetime` 7,349/7,349; Period start/end 0/7,349; instant 0/7,349.

## Probe results

The exact system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items`. Source/FHIR counts matched for all twelve literal itemids: 226559 6,685/6,685; 226560 496/496; 226561 90/90; 226584 0/0; 226563 0/0; 226564 0/0; 226565 0/0; 226567 15/15; 226557 0/0; 226558 0/0; 227488 32/32; 227489 31/31. Total 7,349/7,349. Coding cardinality was one per resource. The target itemids belong to outputevents, and outputevents/datetimeevents itemid overlap was zero.

There were 7,349 source/FHIR rows and 7,317 `(stay_id, charttime)` groups on each side; 32 duplicate groups were preserved. Item `227488` had 32 positive source values, and raw tuple agreement was 7,349/7,349. Grouped `SUM(CASE...)` agreement was 7,317/7,317 exact.

Resource IDs remain opaque and were not used. The ETL casts charttime through `TIMESTAMPTZ`, so DST-gap normalization may be intrinsically unrepresentable; demo impact was 0/7,349 and full-data impact remains to be bounded. Because charttime is the grouping key, any such loss may be essential; do not repair through IDs.

`MIMIC_NOTES.md` was not edited. A provisional dataset note was appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/urine_output.md` for outputevents Observations being dateTime-only. Carryover was written and recorded at `mimic-iv/concepts_fhir/carryover/urine_output/fhir-prober.md` and `carryover.json`.

Artifacts:
- `mimic-iv/concepts_fhir/carryover/urine_output/fhir-prober.md`
- `mimic-iv/concepts_fhir/carryover/urine_output/carryover.json`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/urine_output.md`
