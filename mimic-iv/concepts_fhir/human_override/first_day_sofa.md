# `first_day_sofa` — human override out of `BLOCKED_REPRESENTATION`

- **Applied:** 2026-08-26 00:36 UTC
- **Transition:** `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, `--by human`
- **Attempt:** `concepts/firstday/first_day_sofa/attempt_0002`
- **Canonical SQL:** `mimic-iv/concepts/firstday/first_day_sofa.sql`
- **Fidelity:** 73,157 / 73,181 identical (99.9672%), row counts equal

> **Backfill, written 2026-08-26.** Reconstructed the same day but after the fact,
> from `state/first_day_sofa/state.json`, both attempts' artifacts,
> `MIMIC_NOTES.md:949-1003`, and — new to this entry — a direct read of the
> Pathling encoder source and an end-to-end NDJSON→Delta probe. The `state.json`
> justification paragraph is the contemporaneous record. §2 and §5 go
> substantially beyond it; §7 says exactly where, and §7 also corrects two numbers
> that paragraph got wrong.

This is the **origin entry for the six-decimal Quantity class**.
`human_override/sofa.md` is the same event at hourly grain and defers here for the
encoder forensics.

## 1. The problem

24 of 73,181 ICU stays (0.0328%) come back with a first-day `cardiovascular`
score of 3 where the oracle says 4, and a total `sofa` one point lower to match.
Row counts are equal, the key pairs 1:1, and there are no NULL-only differences and
no missing or extra rows.

The equivalence judge blocked it
(`attempt_0002/evidence/equivalence-judge.md`):

> The loss is non-injective: source rates just above SOFA thresholds 0.1 or 5
> collapse to exact served thresholds. […] The residual changes the clinically
> meaningful cardiovascular component and total SOFA, so it is essential loss
> rather than an ancillary gap.

The mechanism is confirmed exactly as stated. Two things are rejected. The first
is the attribution: the judge cited a `mimic-fhir` ETL line, and the loss is not
there (§2). The second is the conclusion — the essential-loss test is applied to a
difference that is **float32 representation noise in the relational source**, not a
clinical distinction (§3).

## 2. What caused it

### Not the cited `mimic-fhir` statement

The judge cited `mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`,
especially line 94. That is where the rate is selected and written:

```sql
        , ie.rate AS ie_RATE                                    -- line 14
...
            , 'rateQuantity',                                   -- line 91
                CASE WHEN ie_RATE IS NOT NULL THEN
                    jsonb_build_object(
                        'value', ie_RATE                        -- line 94
                        , 'unit', ie_RATEUOM
                        , 'system', 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units'
                        , 'code', ie_RATEUOM
                    )
                ELSE NULL END
```

`ie_RATE` goes into the JSONB unmodified. **Nothing is truncated here.** Verified
against the emitted NDJSON: the distribution ships the full double expansion of
the source `float4`, up to 18 fractional digits. A complete census of
`MimicMedicationAdministrationICU.ndjson.zst` (demo, 20,404 resources, 11,038
carrying a `rateQuantity`), counting fractional digits in the **raw JSON text**
rather than a parsed float:

| fractional digits in NDJSON | resources |
|---|---|
| 1-6 | 2,212 |
| 8-12 | 115 |
| 13-15 | 6,073 |
| 16-18 | 2,638 |
| **more than 6** | **8,826 (80.0%)** |

Sample raw values: `4.0460004806518555`, `124.99999237060547`,
`6.067358493804932`. The precision reaches Pathling intact.

### The encoder

`au.csiro.pathling.encoders.datatypes.DecimalCustomCoder`, in the Pathling source
(checkout at `~/Documents/pathling`, `9.9.0-SNAPSHOT`):

```scala
  val scale: Int = 6                                                    // :131
  val precision: Int = 32                                               // :132
  val decimalType: types.DecimalType =
      DataTypes.createDecimalType(precision, scale)                     // :133
```

Two `val`s in a companion object. Every FHIR `decimal` — `Quantity.value`, `Ratio`
numerator/denominator, all of them — is serialized through
`Decimal.apply(...)` cast to that type (`:67-74`), rounding to six places at
encode time. It is publicly documented behaviour, not an accident:
`site/docs/libraries/io/schema.md:111-112` states "An element of type `decimal`
SHALL be represented as a `DECIMAL` field with a precision of 32 and a scale of
6", and `DecimalCustomCoder.scala:109-129` gives the reasoning (medical decimals
are rarely highly precise; the worst case considered was Location coordinates,
where 6 dp is 10 cm).

**End-to-end, on one resource, verified locally:**

| stage | value | scale |
|---|---|---|
| NDJSON `dosage.rateQuantity.value` | `4.0460004806518555` | 16 |
| Delta `dosage.rateQuantity.value` | `4.046000` | — |
| Delta `dosage.rateQuantity.value_scale` | — | **6** |

(resource `72aff2c0-d201-54c9-b5d3-400774303963`, demo warehouse
`~/warehouses/mimic-iv-demo/delta`, probed 2026-08-26.)

### It is not a missed configuration in our build

`~/Documents/mimic-profiles/scripts/mimic-pipeline/step1_ndjson_to_delta.py` is
the only step that touches the Pathling library. It calls

```python
        pc = PathlingContext.create(
            enable_delta=True, enable_terminology=False, enable_extensions=True
        )
```

There is no decimal option to pass — not on `PathlingContext.create`, not on
`EncodingConfiguration`, not as a Spark conf. `scale` and `precision` are
compile-time constants with no accessor. **No setting in our pipeline could have
avoided this**, and rebuilding the warehouse cannot change it.

### No alternative carrier

- `<field>_scale` is `min(6, source_scale)`, not the source scale — see §5, where
  this turns out to be the reportable defect. It is `6` on every one of the 11,038
  demo rate rows, so it does not even flag that truncation happened.
- `_value_canonicalized` (`STRUCT(value DECIMAL(38,0), scale INTEGER)`) is
  computed **from the already-truncated value**, and is populated only where the
  unit code parses as UCUM: non-NULL on **0 of 2,585** `mcg/kg/min` resources
  (93/93 for `mg/min`). The mimic-units vasopressor rate codes do not parse.
- `dosage.dose.value` carries the same `DECIMAL(32,6)`.
- `inputevents.patientweight` is not served at all, so no combination of `dose`
  and `effectivePeriod` reconstructs a per-kg rate.
- Opaque resource identity is refused as a recovery channel by
  `LOOP_CONTRACT.md:317-333` and `src/mimic_utils/sql_lint.py`.

## 3. Intentional or a bug?

| class | what is lost | verdict |
|---|---|---|
| 1 | on the 24 affected stays: digits that are **float32 representation noise in relational MIMIC-IV**, not recorded clinical fact | **not a loss of information** — see below |
| 2 | `_scale` records `min(6, source)` rather than the source scale, so truncation is not even *detectable* | **bug** — contradicts a documented `SHALL`; see §5 |
| 3 | genuine sub-6-dp precision on any FHIR decimal that has it | **inherent to the served stack** — a Pathling constant, outside `mimic-fhir`, liftable only by Pathling |
| 4 | the ETL renders a `float4` as its full 18-digit double expansion, asserting precision the source does not have | **fixable, arguable** — `mimic-fhir`'s to fix, and it would not clear these rows |

Class 1 decides the override, and it is worth being precise about. `mimiciv_icu.inputevents.rate`
is `FLOAT` — float32, ~7 significant digits. On the affected stays the oracle value
is not "0.1 plus a real increment"; it is the float32 neighbour of 0.1:

```
float32(0.1)         = 0.10000000149011612
next float32 upward  = 0.10000000894069672     ← the oracle's value
1 ULP                = 7.450580596923828e-09
```

and for the dopamine stays, `5.0000004768371582` is exactly `float32(5.0)` plus one
ULP. Nothing in MIMIC records a norepinephrine infusion of 0.100000009 mcg/kg/min
as clinically distinct from 0.1; that eighth decimal is an artifact of storing a
decimal literal in 32-bit binary floating point. Six-place rounding does not
destroy a measurement here — it returns the value to the number the source was
trying to hold. **The served `0.100000` is the more faithful reading of clinical
intent than the oracle's `0.10000000894069672`.**

Classes 2-4 are all repairable, and saying so strengthens the entry rather than
weakening it (`human_override/README.md`, `LOOP_CONTRACT.md:256-315`). None of
them would move these 24 rows: class 2 makes the loss visible, not recoverable;
class 3 is the only one that would recover it and it is not `mimic-fhir`'s to fix;
class 4's shortest-round-trip rendering of `0.10000001` still needs 8 dp and still
would not fit.

## 4. Example of the loss

From `attempt_0002/comparison.full.json` (`diff.samples.differing_conflict`), the
first of the 20 sampled rows:

| | `stay_id` | `cardiovascular` | `sofa` |
|---|---|---|---|
| **relational MIMIC-IV (oracle)** | 35665012 | 4 | 8 |
| **port over MIMIC-on-FHIR** | 35665012 | 3 | 7 |

Every other component (`respiration`, `coagulation`, `liver`, `cns`, `renal`)
agrees. `first_day_sofa.sql` projects no rate columns, so the artifact shows the
consequence and not the cause; the served resource behind it is:

```json
{ "resourceType": "MedicationAdministration",
  "dosage": { "rateQuantity": { "value": 0.100000, "unit": "mcg/kg/min" } } }
```

against an oracle `MAX(rate)` of `0.10000000894069672`. Canonical SOFA scores 4 for
`rate_norepinephrine > 0.1` and 3 for `<= 0.1`; `0.10000000894069672 > 0.1` is
true, `0.100000 > 0.1` is false. Across all 24 stays: 20 have a norepinephrine max
in `(0.1, 0.1000005]` served as `0.100000`, and 4 have a dopamine max of
`5.0000004768371582` served as `5.000000`.

## 5. What a fix would look like

**Nothing here is fixable by a `mimic-fhir` PR**, which is the substance of the
2026-08-26 attribution correction at `MIMIC_NOTES.md:962-964`. Per class:

- **Class 1** — nothing to fix. The information the port lacks is not clinical
  fact in relational MIMIC-IV either.

- **Class 2 — the one worth reporting upstream, and the only outright defect.**
  `site/docs/libraries/io/schema.md:114-116` says, normatively:

  > In addition, an `INT32` field SHALL be included with the suffix `_scale`. This
  > field SHALL be used to store **the scale of the decimal value from the original
  > FHIR data**.

  The implementation does not do that. `DecimalCustomCoder.scala:96-103`:

  ```scala
  private def scaleExpression(inputObject: Expression) =
    Catalyst.staticInvoke(classOf[Math], IntegerType, "min",
      Literal(decimalType.scale) ::                     // 6
        Invoke(Invoke(inputObject, "getValue", …), "scale", …) :: Nil)
  ```

  `min(6, source_scale)` — clamped. The §2 probe is the proof: source scale 16,
  `value_scale` 6. **Consequence: truncation is silent and undetectable.** A
  consumer holding the served row cannot distinguish a source that said
  `0.10000000894069672` from one that said `0.100000`. Had `_scale` recorded 17,
  this port could have identified the 24 unsafe stays and flagged them, instead of
  publishing a confidently wrong score.

  The clamp is not gratuitous — the deserializer at `:85-94` does
  `toJavaBigDecimal.setScale(_scale)`, so an unclamped 17 would fabricate eleven
  zero digits on read-back. The clean fix moves the clamp from write time to read
  time: store the true source scale, and deserialize with
  `setScale(min(_scale, decimalType.scale))`. Round-trip behaviour is unchanged,
  the documented `SHALL` becomes true, and loss becomes detectable with a single
  predicate (`value_scale > 6`). Reading it the other way — that the docs overstate
  what `_scale` does and the code is right — is also a defect, just a documentation
  one; either way there is a real discrepancy to file.

- **Class 3** — a Pathling change: make the decimal scale configurable, or encode
  decimals the way `FlexiDecimal` already does elsewhere in the same codebase
  (`encoders/.../sql/types/FlexiDecimal.java:57-70` — unscaled `DECIMAL(38,0)` plus
  an explicit scale, i.e. arbitrary scale). So the higher-fidelity representation
  is not architecturally new to them; it is already implemented for canonicalized
  quantities. This is a design-change request, weaker than class 2, and worth
  raising in the same report rather than on its own. If it ever lands, both SOFA
  concepts are a plain replay.

- **Class 4** — `mimic-fhir` could render `float4` at shortest round-trip
  precision instead of the full double expansion; `124.99999237060547` asserts 17
  digits for a value carrying about 7. Worth fixing for honesty; it clears no row
  here.

**No port-side fix exists, and this was measured rather than assumed.** Attempt
0001 used the canonical untyped `> 0.1` and recorded 22 conflicts; attempt 0002
used `> CAST(0.1 AS FLOAT)` and recorded 24 — right on 20 of the first set's rows
and wrong on 18 others, and vice versa. Two defensible spellings, neither
correct, because the discriminating digit is not served.

## 6. Numbers

From the full comparisons:

| | attempt_0001 | **attempt_0002** |
|---|---|---|
| identical | 73,159 | **73,157** |
| `differing_conflict` | 22 | **24** |
| `differing_null_only` | 0 | **0** |
| `only_oracle` / `only_candidate` | 0 / 0 | **0 / 0** |
| `cardiovascular` conflicts | 22 | **24** |
| `sofa` conflicts | 22 | **24** |
| tier | `contested` | **`contested`** |

Attempt_0002 residual: **24 of 73,181 stays = 0.0328%**, fidelity 0.999672. Key
`(stay_id)`, classification `keyed`, no `excluded_as_unrepresentable` columns.
Comparator tolerances: relative 0.001, absolute 1e-9, timestamps 1 s, row count
exact. Every affected stay differs by exactly one point on both columns; none
differs by two.

By the §3 classes: class 1 accounts for all 24 rows (20 norepinephrine, 4
dopamine); classes 2-4 account for none. **No post-fix projection**, because §5
establishes there is no fix that recovers a row — the figures are terminal until
Pathling's encoder changes.

Warehouse census (demo, `~/warehouses/mimic-iv-demo/delta`, 2026-08-26):
56,535 `MedicationAdministration` resources, 11,038 carrying a `rateQuantity`,
`max(value_scale) = 6` across all of them, `_value_canonicalized` non-NULL on
0/2,585 `mcg/kg/min` and 93/93 `mg/min`.

## 7. Misc

- **The comparator itself calls these rates equal.** At the run's tolerances
  (`rtol 0.001`, `atol 1e-9`), `0.10000000149011612` against
  `0.10000000894069672` is a relative difference of 7.5e-8 — well inside
  tolerance. The port and the oracle agree on the dose by the loop's own standard
  of numeric equality; they disagree only because a `>` test in canonical SQL has
  no tolerance and cannot have one.
- **Why the loss is acceptable** (`LOOP_CONTRACT.md:481`), term by term. *Row
  inclusion:* unchanged — 73,181 = 73,181, zero `only_oracle`, zero
  `only_candidate`; the cohort is the first-day ICU stay list with no rate
  predicate. *Semantic grain:* unchanged — paired 1:1 on `stay_id`. *Grouping:*
  unchanged — the conflict is confined to the cardiovascular branch and its sum
  into `sofa`; every other component agrees on every row. *Temporal
  carry-forward:* none — `first_day_sofa` has no window (unlike `sofa`, where the
  24-hour window amplifies the same event; see `human_override/sofa.md`).
  *Contamination of representable values:* none — no estimate, no imputation, no
  NULL-for-value; each affected cell holds a well-defined integer one point low.
- **Two corrections to the contemporaneous `state.json` justification.** It cites
  "44,152 demo rate rows" and "0/10,340 mcg/kg/min (372/372 mg/min)". Those counts
  came from a `read_parquet('…/**/*.parquet')` glob, which reads **every Delta file
  version** rather than the current snapshot, and are uniformly 4× too high: the
  true figures are 11,038, 0/2,585 and 93/93 (§6), and 226,140 / 4 = 56,535
  resources confirms the factor exactly. The NDJSON census independently found
  11,038 `rateQuantity` values, matching. **No conclusion changes** — the ratios
  are identical, `max(value_scale)` is 6 either way, and zero is zero. The same
  inflated numbers are recorded at `MIMIC_NOTES.md:996-1000`, corrected there on
  2026-08-26, and are repeated in `sofa`'s `state.json` justification, which is
  immutable and stands with this note against it.
- **Consistency, and what this entry gates.** `sofa` was blocked on the identical
  event and overridden on 2026-08-26 citing this ruling
  (`human_override/sofa.md`); `sofa` in turn gates `sepsis3`. So although the
  contemporaneous justification correctly said "nothing depends on
  `first_day_sofa`", this ruling became the precedent for two further concepts
  within the day. That is an argument for its being right, not for its being
  broader than it is: both consumers are SOFA cardiovascular scoring off the same
  vasopressor rates.
- **The vasoactive dependencies do not carry this.** `dobutamine`, `dopamine`,
  `epinephrine` and `norepinephrine` are `COMPLETED_WITH_DIVERGENCE (judge)` for
  the **`linkorderid`** omission, a different event. Their comparisons could not
  have surfaced the decimal cap — their diffs are key-alignment artifacts with 0
  `differing_conflict`, so rate values were never compared row to row. The judge
  was right that they "do not explain these target rows"; the explanation is one
  layer below all of them.
- **Not a declaration.** `unrepresentable.json` is the wrong instrument: the
  columns are not 100% NULL, so the comparator would reject it as
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:420-423,440-446`).
- **Added by this backfill** (not in the contemporaneous justification): the
  NDJSON census and the end-to-end probe in §2, the encoder source reading, the
  finding that our own pipeline had no lever, the class 2 `_scale` defect and its
  proposed fix in §5, the `FlexiDecimal` precedent, the class 4 observation about
  the ETL's spurious 18-digit rendering, and the count corrections above. The
  ruling itself is unchanged.
- **Upstream reporting.** Class 2 is filed-shaped as it stands: a documented
  `SHALL`, an implementation that contradicts it, a two-line reproduction, and a
  patch that preserves round-trip behaviour. Pathling is a CSIRO product, so this
  is an internal report rather than a cold issue. **Not yet filed as of
  2026-08-26** — this file is the source material, not evidence that it was sent.
