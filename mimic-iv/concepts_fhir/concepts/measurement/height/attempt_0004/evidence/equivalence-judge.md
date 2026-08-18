# Equivalence-judge evidence

The independent judge returned **accept** for the attributed review. Provenance
passes: `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts source
`charttime` through `TIMESTAMPTZ`, and line 67 writes the transformed value to
`Observation.effectiveDateTime`, which the port reads through
`Observation.effective.ofType(dateTime)`. Rarity passes: 2/33,474 rows
(0.006%) differ, both are spring-forward 02:xx to 03:xx shifts, and the
comparator replay explains every conflict with zero residual.

Essentiality does not block this port. There are no missing or candidate-only
rows, no subject/stay or grouping changes, and no height-value conflicts; only
two charttime values differ. The judge's cited acceptance reason is:

> `height` attempt 0004 differs only on 2/33,474 `charttime` values (0.006%).
> `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts source `charttime`
> through `TIMESTAMPTZ`, and line 67 writes it to `Observation.effectiveDateTime`,
> the element read by the port. The comparator replayed this
> America/New_York DST-gap transformation over every conflicting row with zero
> residual. Height values, row inclusion, grouping, subject/stay assignment,
> and natural grain remain equal. The port uses the required direct
> `TIMESTAMP_NTZ` mapping and does not infer values from opaque resource ids,
> so it is faithful to the served data.

Final verdict: `accept`, with no divergent dependencies and no new dataset-wide
quirk identified.
