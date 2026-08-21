# Mismatch diagnostician evidence

## Diagnosis

`vasoactive_agent` attempt_0001 has **no fixable target-port construction, mapping, join, or SQL error**. Its unkeyed residual is the combined downstream effect of divergences already present in the seven completed dependency outputs:

1. Six-decimal ICU MedicationAdministration Quantity precision causes widespread bit-level rate differences, although the dependency comparisons established that representable rates are within comparator tolerance.
2. Upstream `TIMESTAMPTZ` normalization moved endpoints in **112 selected dependency administrations**. These shifts propagate through the parent’s `UNION DISTINCT`, `LEAD`, and seven interval-containment joins.
3. One phenylephrine source administration requires unavailable `patientweight`; its honest NULL rate can propagate to multiple parent intervals, but it does not alter boundaries or grain.

The comparator cannot separate these effects because the concept has no key and the DST-induced structural differences prevent global residual pairing. Therefore the 594,287 candidate residual tuples are not evidence that the target invented that many rows.

### Target SQL assessment

The target faithfully reproduces the canonical construction:

- Boundary union: canonical `vasoactive_agent.sql:9-66`; candidate `concept.sql:70-110`.
- Per-stay `LEAD`: canonical `:69-80`; candidate `:111-119`.
- Seven containment joins: canonical `:96-124`; candidate `:120-160`.
- Final non-null-end filter: canonical `:127`; candidate `:161`.

The extra identifier-support joins do not introduce fan-out. The ICU ETL emits one Encounter per `icustays` row, with one ICU identifier, at `mimic-fhir/sql/fhir_encounter_icu.sql:1,27-30,44,65-80`. Resource keys are used only for equality joins; no identity value is parsed or reconstructed.

The target MedicationAdministration ViewDefinition is unused by `concept.sql`, so its presence cannot change candidate rows. The Encounter ViewDefinition correctly obtains `stay_id` from the ICU identifier rather than from a resource key.

### Inherited divergence

Full dependency artifacts establish the following timing transformations:

- Norepinephrine: 58 unique rows, 33 shifted starts and 34 shifted ends, nine with both (`norepinephrine/attempt_0003/evidence/mismatch-diagnostician.md:24-31`).
- Phenylephrine: 47 rows across 19 stays (`MIMIC_NOTES.md:523-528`).
- Milrinone: four underlying administrations (`milrinone/attempt_0002/evidence/equivalence-judge.md:5`).
- Dobutamine: one shifted start-key row and one preceding endtime-conflict row, representing two administrations around one shared boundary (`dobutamine/attempt_0003/comparison.full.json:78-126`).
- Vasopressin: one shifted endtime row (`vasopressin/attempt_0002/comparison.full.json:33-75`).
- Dopamine and epinephrine have no documented timing residual.

Total: **112 selected source administrations moved by the cast**. This is about 0.018% of the 614,600 dependency rows and is consistent with DST-gap rarity.

The ETL cause is load-bearing: `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9` casts source endpoints through `TIMESTAMPTZ`, and `:61-69` writes only those transformed values to `effectivePeriod`/`effectiveDateTime`. The original wall times are absent from semantic FHIR elements and cannot be recovered by any permissible query.

Those changed boundaries feed the target’s `UNION DISTINCT`, `LEAD`, and containment joins, explaining the candidate’s +21 row delta and the reported marginal drift in `stay_id` (23), `starttime` (169), and `endtime` (167). They also alter which rates cover an interval.

The remaining large exact rate drift is explained by Quantity materialization at six-decimal precision, documented in `MIMIC_NOTES.md:850-862` and written from the ETL rate at `fhir_medication_administration_icu.sql:14,91-99`. Every completed dependency either reproduced representable rates within tolerance or documented its specific exception. The parent comparator’s exact residual alignment could not apply those tolerances because the timing residual prevented pairing.

### Coverage and essentiality

- `linkorderid` is absent upstream (`MIMIC_NOTES.md:833-848`; ETL `:7-23,38-103`) but is irrelevant here: the canonical parent neither selects nor consumes it.
- Norepinephrine’s two full-data `mg/kg/min` rows both have `patientweight=1`, so raw FHIR rate is exact (`norepinephrine/attempt_0003/evidence/mismatch-diagnostician.md:3-7`).
- Phenylephrine has one exercised `mcg/min` row whose exact normalized rate is unavailable because the ETL does not select or serialize `patientweight` (`fhir_medication_administration_icu.sql:7-23,38-103`). Its dependency correctly emits NULL. The target may propagate that NULL through its phenylephrine containment join at `concept.sql:149-152`, but timing and row inclusion remain intact, so this is an ancillary candidate coverage gap rather than essential loss.
- The rate-null `effectiveDateTime` branch would lose source `starttime`, but the completed dependency evidence identifies it as unexercised for these selected streams. It does not explain this review.
- The proven DST transformation changes timing and interval assignment, but `LOOP_CONTRACT.md:256-315` explicitly excludes proven DST damage from essential-loss blocking.

There is no useful new-attempt remedy. Retrying the same target mapping cannot recover source wall times, discarded numeric precision, or row-specific patientweight. The upstream remedy would be to preserve naïve source wall times, retain sufficient Quantity precision, and serialize the row-specific patientweight; after rebuilding the dependencies, the current parent overlay should remain valid.

## Evidence block

Concept `vasoactive_agent`, attempt `0001`. Comparator verdict `review`, tier `contested`, classification `unavailable_no_key`; schema matched. Oracle row count was 665,529 and candidate row count 665,550. Divergence classes were 594,266 `only_oracle` and 594,287 `only_candidate`; residual pairing attempted but paired zero rows. Because this is an unkeyed multiset comparison, these are ambiguous residual halves rather than demonstrated missing and invented rows.

Root cause: upstream transformation and precision loss inherited from the seven completed medication dependencies, amplified by the canonical interval overlay, plus one ancillary propagated phenylephrine patientweight gap. Exact locations are `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69` for irreversible timestamp normalization, `:14,91-99` for the rate Quantity path whose served representation is six-decimal, and `:7-23,38-103` for omission of patientweight. Propagation occurs in candidate `concept.sql:70-161`, matching canonical `mimic-iv/concepts/medication/vasoactive_agent.sql:9-127`.

Recommended fix: none in a new target attempt. Route the current result to the equivalence judge. Do not parse or reconstruct resource IDs. A true fix requires upstream ETL and dependency rebuilds, not target SQL changes.

Classification: **upstream transformation loss**, with an ancillary **candidate coverage gap** for the exercised phenylephrine patientweight row; **not a fixable target-port bug**.

Carryover invalidation: **none**. No fragment entry was appended and no commit was made.
