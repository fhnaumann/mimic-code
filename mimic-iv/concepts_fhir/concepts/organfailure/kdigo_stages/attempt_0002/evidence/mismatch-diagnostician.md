# Mismatch diagnostician — `kdigo_stages` attempt `0002`

## Diagnosis

**Root cause:** The current divergence is wholly inherited upstream
`TIMESTAMPTZ` spring-forward normalization, propagated through the three
completed dependencies and this consumer's event-axis and six-hour windows;
the non-DST `kdigo_uo` precision defect from attempt 0001 is fixed. This is
**upstream transformation loss**, not a `kdigo_stages` or dependency port bug.

The comparator correctly reports a contested review because this concept is
unkeyed. Its 1,703 `only_oracle` and 1,460 `only_candidate` tuples are exact
full-tuple multiset residuals, not separable missing/invented-row classes. The
243-row count delta is evidence to account for, not a gate.

## Current-attempt and dependency re-check

Attempt 0002 has the same consumer SQL as attempt 0001. It faithfully preserves
the canonical construction:

- the creatinine, urine-output, and retained-CRRT event-axis `UNION DISTINCT` at
  `concept.sql:87-102`;
- exact dependency alignment on ICU encounter identity plus `charttime` at
  `concept.sql:140-151`;
- the canonical urine-output stage branches at `concept.sql:65-73`; and
- the subject-level, relative-to-ICU-intime six-hour `RANGE` smoothing window at
  `concept.sql:124-136`.

The current staged dependency manifest identifies `crrt` attempt 0007,
`kdigo_creatinine` attempt 0002, and the now-fixed `kdigo_uo` attempt 0004.
Their staged SQL and accepted full-run evidence show:

- `kdigo_creatinine` preserves the strict prior 48-hour and seven-day windows
  at its `concept.sql:48-72`; its accepted full result has 145 shifted
  `charttime` conflicts plus the bounded baseline-window consequences.
- `crrt` groups selected chartevents by ICU stay and served charttime and applies
  the canonical `MAX` pivot at its `concept.sql:42-93`; its accepted result has
  zero residual after DST key/collision attribution.
- `kdigo_uo` attempt 0004 preserves `LAG`, 6/12/24-hour `RANGE` windows, and the
  half-open weight join at its `concept.sql:24-92,141-144`. Its six internal
  duration/rate casts now use `DECIMAL(38,9)` at `:69-92,102-134`, eliminating
  the premature-rounding defect. Its accepted full replay found 395 moved
  outputevents source rows forming 393 urine-output groups and closed all 393
  oracle-only, 157 candidate-only, and 1,061 propagated conflict rows with zero
  residual.

A full-data comparison of the attempt 0001 and attempt 0002 candidate Parquet
outputs found **exactly four changed tuples and no others**. The four corrected
rates are:

| stay_id | charttime | attempt 0001 | attempt 0002 / oracle |
|---:|---|---:|---:|
| 31003138 | 2182-04-21 21:00 | `uo_rt_24hr=1.2863` | `1.2864` |
| 31463721 | 2174-05-12 20:40 | `uo_rt_24hr=0.0312` | `0.0313` |
| 33150909 | 2138-07-04 20:00 | `uo_rt_24hr=1.2139` | `1.2140` |
| 36685533 | 2188-05-03 09:35 | `uo_rt_12hr=0.9513` | `0.9514` |

All four attempt-0002 tuples match the full oracle exactly. This independently
checks that the dependency retry removed the prior precision issue without
changing the target SQL or perturbing the DST-affected population.

## Full residual closure

The full-oracle source replay established the following rare normalized inputs
selected by this consumer:

- 145 labevents-backed `kdigo_creatinine` timestamps;
- 393 `kdigo_uo` event timestamps, originating from 395 selected outputevents
  rows that collapse to 393 urine-output groups;
- 26 retained CRRT timestamps backed by selected chartevents; and
- 10 ICU `intime` values.

That is **574 moved inputs at the `kdigo_stages` consumer grain**. The current
dependency evidence independently preserves the same source populations, and
the attempt-to-attempt full-output check proves that only the four corrected
non-DST rates changed.

Through the current `kdigo_stages` SQL, those normalized inputs account for:

- **1,697 of 1,703 `only_oracle` tuples**; and
- **1,454 of 1,460 `only_candidate` tuples**.

The propagation is not one moved input to one output tuple. Dependency lookback
windows first change baselines, rolling volumes, durations, rates, and weight
interval selection. Then `kdigo_stages`'s `UNION DISTINCT` can delete or create
an event-axis time, its exact joins can move component values between rows, its
stage cases can change, and its relative-time `RANGE` can carry a changed stage
into later rows. Collisions at normalized 03:xx times explain why the two sides
do not balance.

The remaining **six tuples per side** are non-semantic exact-multiset artifacts,
not unexplained source loss. They are the six rows for stay `34702262` from
2116-04-29 21:00 through 2116-05-01 03:30 where Spark carries a creatinine
baseline as `0.49999999999999994` and the oracle carries `0.5`; every output is
otherwise the same and the values are within the comparator's relative
tolerance. Thus the current closure is exact:

```text
only_oracle:    1,697 DST-propagated + 6 within-tolerance = 1,703
only_candidate: 1,454 DST-propagated + 6 within-tolerance = 1,460
semantic residual after attribution and tolerance: 0 / 0
```

The 243-row delta is entirely inside the attributed set
(`1,697 - 1,454 = 243`). There is no remaining rounding, join, filter, coding,
or mapping residual.

## Upstream transformation and non-recoverability

The load-bearing upstream statements are:

- `mimic-fhir/sql/fhir_observation_labevents.sql:15` casts
  `labevents.charttime` through `TIMESTAMPTZ`; line 121 writes only that
  normalized value to `Observation.effectiveDateTime`. The possible specimen
  alternative is not an original-time witness:
  `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` aggregates the source time,
  applies the same cast, and writes the normalized value.
- `mimic-fhir/sql/fhir_observation_outputevents.sql:9` casts
  `outputevents.charttime` through `TIMESTAMPTZ`; line 60 writes it to
  `Observation.effectiveDateTime`. Lines 62-65 retain the quantity, not the
  original charttime.
- `mimic-fhir/sql/fhir_observation_chartevents.sql:9` applies the same cast to
  chartevents; line 67 writes the result to `Observation.effectiveDateTime`.
- `mimic-fhir/sql/fhir_encounter_icu.sql:31` applies the cast to
  `icustays.intime`; line 98 writes only that value to `Encounter.period.start`.

For a source wall time in the New York spring-forward gap, these statements
replace 02:xx with 03:xx before FHIR serialization. `issued` is transformed
`storetime`, not a copy of `charttime`; specimen timing is normalized too; and
the ICU identifier carries only `stay_id`. A normalized 03:xx is therefore
indistinguishable from a genuine source 03:xx by any allowed FHIR query. The
resource/reference UUIDs are opaque identity and cannot be inverted or matched
against guessed timestamps. The original wall times are unrecoverable.

## Classification, essentiality, and routing

Classification: **upstream transformation loss**. The shifted values do affect
row inclusion, event grain, clinical stage values, and temporal carry-forward,
but `LOOP_CONTRACT.md` explicitly exempts proven DST normalization and all
closed second-order consequences from the essential-loss block. The six
additional exact residual pairs are within declared comparator tolerance and
do not represent source loss. There is no essential non-DST residual.

Recommended routing: send attempt 0002 directly to the equivalence judge with
this closure. Do not create another `kdigo_stages` attempt, reopen a dependency,
or change the consumer SQL. No carryover analysis stage is at fault; invalidate
**none**.

## Evidence block

Concept `kdigo_stages`, attempt `0002`; tier `contested`; classification
`unavailable_no_key`; schema matched; oracle rows 4,011,255, candidate rows
4,011,012; divergence classes present are 1,703 `only_oracle` and 1,460
`only_candidate`, with keyed conflict/null classes unavailable for this unkeyed
full-tuple comparison.

Root cause diagnosis: 574 selected timing inputs moved by the cited upstream
`TIMESTAMPTZ` transformations. Their dependency-window, event-axis, exact-join,
stage, and smoothing propagation explains 1,697 oracle and 1,454 candidate
residual tuples. Six further tuples per side are same-natural-row floating
representations within comparator tolerance, leaving semantic residual 0/0.
The attempt-0001 precision defect is closed: all four tuples changed by
`kdigo_uo` attempt 0004 now equal the oracle.

ETL locations checked: `fhir_observation_labevents.sql:15,121`,
`fhir_specimen_lab.sql:9,18,58`,
`fhir_observation_outputevents.sql:9,60,62-65`,
`fhir_observation_chartevents.sql:9,67`, and
`fhir_encounter_icu.sql:31,98`. The original source wall time is absent from
FHIR and cannot be recovered by any allowed query; resource/reference ids were
treated as opaque.

Read and checked `AGENTS.md`, `LOOP_CONTRACT.md`, the `concept-equivalence`
skill, the `kdigo_stages` oracle-manifest entry, canonical and attempt SQL,
attempt 0002 ViewDefinitions, shape/full/HPC metadata and all current evidence,
both attempts' comparison context, the attempt 0001 diagnosis, both carryover
analyses, the current staged dependency manifest and staged SQL/accepted
full-run evidence for `crrt` 0007, `kdigo_creatinine` 0002, and `kdigo_uo` 0004,
and the exact cited `mimic-fhir` SQL statements.

Curated `MIMIC_NOTES.md` entries checked were the `TIMESTAMP_NTZ`/irreversible
DST entry, chartevents second-order propagation, labevents prior-window
propagation, opaque resource identity, and essential-loss policy. They explain
the current divergence when combined with the current accepted dependency
replays. Task-supplied sibling-fragment claims were treated only as leads and
were not cited as evidence.

Three successful full-data diagnostic probes were spent: one chose between an
isolated intended dependency fix and broader output drift; one chose between
oracle-corrected values and merely different values; and one chose between a
non-DST semantic residual and within-tolerance natural-row peers. One initial
oracle-attach command failed before execution because of SQL quoting. No
attempt, ViewDefinition, comparator, or end-to-end run was recomputed.

Essentiality: contract-exempt proven DST damage only; no essential non-DST
loss. Recommended action: equivalence judge, with no retry and no carryover
invalidation. Classification: **upstream transformation loss**.

Artifact written:
`mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0002/evidence/mismatch-diagnostician.md`.
No new dataset-wide quirk was established beyond the existing curated notes and
owned fragment, so `MIMIC_NOTES.d/kdigo_stages.md` was left unchanged. No other
repository file was modified and no commit was made.
