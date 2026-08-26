# `sofa` — human override out of `BLOCKED_REPRESENTATION`

- **Applied:** 2026-08-26
- **Transition:** `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, `--by human`
- **Attempt:** `concepts/score/sofa/attempt_0002`
- **Canonical SQL:** `mimic-iv/concepts/score/sofa.sql`
- **Fidelity:** 6,042,764 / 6,043,902 identical (99.9812%), row counts equal

Same cause and same ruling as `human_override/first_day_sofa.md`, the override
applied earlier the same day, which is the **origin entry for this class** and
carries the encoder forensics, the end-to-end NDJSON→Delta probe and the
stay-level accounting this file leans on. `MIMIC_NOTES.md:967-1003` carries the
shared encoder fact. This file states the `sofa` specifics: the same event at
hourly grain, amplified by the canonical 24-hour window.

## 1. The problem

1,138 of 6,043,902 hourly SOFA rows (0.0188%) come back with a `cardiovascular`
score one point below the oracle's, or with a `cardiovascular_24hours` /
`sofa_24hours` that inherits such an hour through the score's 24-row window. Every
row is present, every other component agrees, and no cell is NULL where the oracle
holds a value.

The equivalence judge blocked the concept
(`attempt_0002/evidence/equivalence-judge.md`), having agreed the cause is
upstream and not a port defect:

> The divergence is intrinsic rather than a remaining SOFA SQL/ViewDefinition
> bug. […] The 24-row carry-forward makes the lost threshold side alter
> clinically meaningful cardiovascular and total SOFA outputs. Under the
> contract's essential-loss rule, publishing ordinary SOFA values would conceal
> ambiguity, so the judge blocked the concept despite the small affected
> fraction.

Its factual findings are confirmed in full. What is rejected is the last step:
the essential-loss test applied to loss the loop has already accepted upstream,
which is the failure mode `LOOP_CONTRACT.md:1002-1035` was written to stop, and
the treatment of a difference the comparator's own equality test calls *no
difference at all* (§7) as a clinical distinction.

## 2. What caused it

**Not a `mimic-fhir` statement.** The judge and the diagnostician both cite
`mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`, especially
line 94 — the statement that writes the ICU `inputevents.rate` into
`MedicationAdministration.dosage.rateQuantity.value`. That citation locates the
value's provenance, not the loss. The statement writes `ie.rate` into JSONB
unmodified; nothing is discarded there. (The `mimic-fhir` submodule is not
checked out in this working tree, so the line is cited from the attempt evidence
and `MIMIC_NOTES.md:949-964` rather than quoted here.)

The loss is **Pathling's encoder**, one layer below. Every FHIR `decimal`
materializes in the served Delta warehouse as `DECIMAL(32,6)`, rounded to six
places at encode time (`MIMIC_NOTES.md:967-1003`). Probed directly against the
rebuilt demo warehouse on 2026-08-26:

```
MedicationAdministration.dosage.rateQuantity
  STRUCT(value DECIMAL(32,6), value_scale INTEGER, …,
         _value_canonicalized STRUCT(value DECIMAL(38,0), scale INTEGER),
         _code_canonicalized VARCHAR)
```

The scale cap is `val scale: Int = 6` in the companion object of
`au.csiro.pathling.encoders.datatypes.DecimalCustomCoder` — a compile-time
constant with no accessor, no `PathlingContext.create` option and no Spark conf.
**No `mimic-fhir` patch, no warehouse rebuild and no setting in our own
`step1_ndjson_to_delta.py` lifts it**, which is why `TODO_upstream_fix_rerun.md`
lists ICU `MedicationAdministration` Quantity decimal scale under "still open
upstream, deliberately" and holds `sofa` out of the replay waves.
`human_override/first_day_sofa.md:§2` carries the source reading and an
end-to-end NDJSON→Delta probe showing a source scale of 16 served as `4.046000`
with `value_scale` 6.

No alternative carrier:

- `<field>_value_scale` is the *stored* scale, not the source scale — `6` on all
  11,038 demo rate rows. Recording `min(6, source_scale)` rather than the source
  scale contradicts a documented `SHALL` and is the one outright upstream defect
  in this class; see `human_override/first_day_sofa.md:§5`.
- `_value_canonicalized` is computed from the already-truncated value, and is
  non-NULL on **0 of 2,585** `mcg/kg/min` resources (93/93 for `mg/min`). The
  mimic-units codes for vasopressor rates do not parse as UCUM.
- `dosage.dose.value` carries the same `DECIMAL(32,6)`, and
  `inputevents.patientweight` is not served at all, so amount ÷ weight ÷
  `effectivePeriod` cannot reconstruct a per-kg rate even in principle.
- Resource identifiers carry identity only; inversion is refused by
  `LOOP_CONTRACT.md:317-333` and `src/mimic_utils/sql_lint.py`.

## 3. Intentional or a bug?

Ruled per class. The first class is the one that decides the override.

| class | what is lost | verdict |
|---|---|---|
| 1 | the digits below 6 dp in `rateQuantity.value` — but on the affected rows those digits are **float32 representation noise in the relational source**, not recorded clinical fact | **not a loss of information** — see below |
| 2 | the digits below 6 dp on any row where the source scale genuinely exceeds six | **inherent to the served stack** — a Pathling encoder constant, outside `mimic-fhir`; repairable only by Pathling |
| 3 | `inputevents.patientweight`, which would let a consumer rebuild a rate from `dose` | **fixable, arguable** — a real omission, but repairing it recovers nothing, because `dose.value` carries the same six-place cap |

Class 1 is the whole of the observed divergence and is worth stating precisely.
`mimiciv_icu.inputevents.rate` is `FLOAT` — float32, ~7 significant digits. The
oracle value on the affected rows is not "0.1 plus a real increment"; it is the
float32 neighbour of 0.1:

```
float32(0.1)          = 0.10000000149011612      ← candidate
next float32 upward   = 0.10000000894069672      ← oracle
1 ULP                 = 7.450580596923828e-09
```

The oracle's value sits **one unit in the last place** above the cut-point.
Nothing in the source records a norepinephrine infusion of 0.100000009 mcg/kg/min
as clinically distinct from 0.1; that eighth decimal is an artifact of storing a
decimal literal in float32. Six-place rounding does not destroy a measurement
here — it lands the value back on the number the source was trying to hold. The
served `0.100000` is, if anything, the more faithful reading.

The grading trap of `human_override/README.md` cuts the usual way: class 2 is
*repairable in principle*, and saying so strengthens the entry rather than
weakening it (`LOOP_CONTRACT.md:256-315`). But class 2 is not what produced these
1,138 rows, and no `mimic-fhir` PR can be opened against class 1 or class 2 —
only against class 3, which would change no output.

## 4. Example of the loss

A real affected row, from `attempt_0002/comparison.full.json`
(`diff.samples.differing_conflict[0]`):

| | `stay_id` | `starttime` | `rate_norepinephrine` | `cardiovascular` | `cardiovascular_24hours` | `sofa_24hours` |
|---|---|---|---|---|---|---|
| **relational MIMIC-IV (oracle)** | 36918249 | `2116-04-07 21:00` | `0.10000000894069672` | 4 | 4 | 4 |
| **port over MIMIC-on-FHIR** | 36918249 | `2116-04-07 21:00` | `0.10000000149011612` | 3 | 3 | 3 |

`meanbp_min` is 31.0 on both sides; `gcs_min` 15.0 on both; every other component
is identical. The served resource holds the rate at the encoder's scale:

```json
{ "resourceType": "MedicationAdministration",
  "dosage": { "rateQuantity": { "value": 0.100000, "unit": "mcg/kg/min" } } }
```

Canonical `sofa.sql:278-285` tests `rate_norepinephrine > 0.1` for 4 points and
`<= 0.1` for 3. `0.10000000894069672 > 0.1` is true; `0.100000 > 0.1` is false.
One point, on the strength of one ULP.

The same stay carries the divergence for the following twelve hours in the
sample, because the infusion continues — and stay 39022990 shows the window
effect on its own: at `2178-06-19 06:00`–`11:00` the hourly `cardiovascular`
agrees exactly (0 = 0, 1 = 1) while `cardiovascular_24hours` and `sofa_24hours`
still differ, carrying an earlier divergent hour through
`sofa.sql:370-375`'s `ROWS BETWEEN 23 PRECEDING AND 0 FOLLOWING`.

## 5. What a fix would look like

**Nothing here is fixable by a `mimic-fhir` PR**, which is the substance of the
2026-08-26 attribution correction at `MIMIC_NOTES.md:962-964`. Stated per class:

- **Class 1** — nothing to fix. The information the port lacks does not exist as
  clinical fact in relational MIMIC-IV either.
- **Class 2** — a Pathling change: make the decimal scale configurable rather than
  a fixed `DECIMAL(32,6)`, or encode decimals the way `FlexiDecimal` already does
  in the same codebase. Separately and more sharply, `_scale` should record the
  source scale as the docs say it does, which would at least make the truncation
  *detectable*. Both are upstream library changes, not `mimic-fhir` SQL repairs;
  `human_override/first_day_sofa.md:§5` states them in filable form. If either
  lands, `sofa` is a plain replay.
- **Class 3** — `fhir_medication_administration_icu.sql` could serve
  `inputevents.patientweight` (as a `dosage.dose` denominator, a `Ratio`, or an
  extension). Worth doing on its own merits; it would not move a single row here,
  since the reconstructed rate would be built from decimals under the same cap.

**No port-side fix exists, and this was measured rather than assumed.**
Attempt 0001 used the canonical untyped literals and recorded 1,938 conflicts
(535 on `cardiovascular`); attempt 0002 typed the `15`, `0.1`, `5` and `0`
thresholds as `CAST(… AS FLOAT)` (`attempt_0002/concept.sql:232-242`) and
recorded 1,138 (294 on `cardiovascular`). The cast fixed a real local Spark
defect and cut the residual by 41%, and it cannot close the rest: no cast,
literal typing, or tolerance recovers a digit that is not served. The stay-grain
sibling ran the same experiment to the same conclusion in the other direction —
`first_day_sofa` went 22 conflicts to 24, right on 20 and wrong on 18 others.

## 6. Numbers

From `attempt_0002/comparison.full.json`:

| | rows | of 6,043,902 |
|---|---|---|
| identical | 6,042,764 | 99.9812% |
| `differing_conflict` | 1,138 | 0.0188% |
| `differing_null_only` | 0 | — |
| `only_oracle` / `only_candidate` | 0 / 0 | — |
| `excluded_as_unrepresentable` | 0 columns | — |

Per column, and against the previous attempt:

| column | attempt 0001 | attempt 0002 | of 6,043,902 |
|---|---|---|---|
| `cardiovascular` | 535 | **294** | 0.0049% |
| `cardiovascular_24hours` | 1,598 | **1,022** | 0.0169% |
| `sofa_24hours` | 1,598 | **1,022** | 0.0169% |
| `rate_norepinephrine` | 1 | **1** | 0.0000% |
| total `differing_conflict` | 1,938 | **1,138** | 0.0188% |

Classification `keyed`, key `(stay_id, starttime)`, tier `contested`,
`judge_required: true`, `diagnostician_required: true`. Comparator tolerances on
this run: relative `0.001`, absolute `1e-9`, timestamps 1 s, row count exact.

By the §3 classes: class 1 accounts for all 1,138 rows; classes 2 and 3 account
for none of them. **No post-fix projection is offered**, because §5 establishes
there is no fix to project — the figures above are terminal until Pathling's
encoder changes.

The distinct-stay count is not derivable from the artifact, which samples 20
conflict rows (two stays). The stay-grain measure of the same event is
`first_day_sofa` attempt_0002: **24 of 73,181 stays (0.0328%)**, all within
5e-7 of a cardiovascular cut-point — 20 with a norepinephrine max in
`(0.1, 0.1000005]` served as `0.100000`, and 4 with a dopamine max of
`5.0000004768371582`, which is exactly `float32(5.0)` plus one ULP, served as
`5.000000`.

## 7. Misc

- **The comparator itself calls these rates equal.** At the run's tolerances
  (`rtol 0.001`, `atol 1e-9`), `0.10000000149011612` vs `0.10000000894069672` is
  a relative difference of 7.5e-8 and is *within tolerance* — which is why
  `rate_norepinephrine` conflicts on 1 row rather than on all of them, even
  though the sampled rows all show the ULP difference. The port and the oracle
  agree on the dose by the loop's own standard of numeric equality. They disagree
  only because a `>` test in canonical SQL has no tolerance and cannot have one.
  Blocking on that is blocking on a difference the comparator was configured to
  regard as noise.
- **Why the loss is acceptable** (`LOOP_CONTRACT.md:481`), term by term. *Row
  inclusion:* unchanged — 6,043,902 = 6,043,902, `only_oracle` and
  `only_candidate` both 0; the cohort is `icustay_hourly`, with no rate
  predicate. *Semantic grain:* unchanged — paired 1:1 on
  `(stay_id, starttime)`. *Grouping:* unchanged — conflicts are confined to the
  cardiovascular branch; `respiration`, `coagulation`, `liver`, `cns` and `renal`
  agree on every row, hourly and 24-hour alike. *Temporal carry-forward:* this is
  the one term that moves, and it is stated rather than minimised — the 24-row
  window turns 294 divergent hours into 1,022 divergent 24-hour rows.
  `LOOP_CONTRACT.md:1030-1033` rules on exactly this: "a dependent may equally
  show *more* rows than its dependency where its SQL fans out. Judge the event,
  then count the rows it explains through this concept's SQL." *Contamination:*
  none — no estimate, no imputation, no NULL-for-value; every affected cell holds
  a well-defined integer score that differs by one.
- **Consistency with `first_day_sofa`.** Same encoder, same cut-points, same
  drug, same one-point delta, accepted `--by human` on 2026-08-26 at 00:36 and
  recorded at `MIMIC_NOTES.md:1000-1003` as the worked example for this class.
  Blocking `sofa` on the identical event would be the split
  `LOOP_CONTRACT.md:512-516` rules against, and it would leave the published
  table asserting that the same divergence is acceptable at stay grain and
  disqualifying at hourly grain.
- **Consistency with the vasoactive dependencies, stated precisely.**
  `dobutamine`, `dopamine`, `epinephrine` and `norepinephrine` are all
  `COMPLETED_WITH_DIVERGENCE (judge)` — but for the *`linkorderid`* omission, a
  different upstream event. Their comparisons could not have surfaced the decimal
  cap: their diffs are key-alignment artifacts with 0 `differing_conflict`, so
  the rate values were never compared row to row. The inheritance argument here
  therefore rests on `first_day_sofa`'s acceptance, not on theirs, and this entry
  does not claim otherwise.
- **The attribution gap, stated rather than papered over.**
  `diff.conflict_attribution` records `complete: false`, `attributed_rows: 0`,
  `cause: upstream_timestamptz_dst_shift` — the comparator replayed only the DST
  hypothesis, which is not the mechanism here and explained nothing. The
  1,138-row attribution to the decimal cap is the diagnostician's reasoning
  (`attempt_0002/evidence/mismatch-diagnostician.md`) plus the 20 sampled rows,
  every one of which fits it, and not a row-by-row replay. What would close it: a
  cut-point-proximity check over the full candidate on `/scratch3`, confirming
  every one of the 294 `cardiovascular` conflicts has a vasoactive rate within
  5e-7 of 0.1, 5 or 15. That check is cheap and was not run before this override;
  the override is taken on the strength of the mechanism, the samples, and the
  identical stay-grain result, and a reader who wants the row-level accounting
  should know it is the piece that is missing.
- **What downstream inherits.** `sepsis3` is the only consumer and is `PENDING`
  with 0 attempts; it was gated by this block and is unblocked by this override.
  Its judge must be told that `sofa` is a divergent dependency and that
  cardiovascular/total SOFA rows traceable to this event are inherited, not
  `sepsis3`'s own (`LOOP_CONTRACT.md:988-1000`).
- **Not a declaration.** `unrepresentable.json` is the wrong instrument: the
  columns are not 100% NULL, so the comparator would reject it as
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:420-423,440-446`).
- **Probe provenance.** The warehouse figures in §2 are from the 2026-08-26 direct
  schema and data probe of
  `~/warehouses/mimic-iv-demo/delta/MedicationAdministration.parquet`. They are
  demo-warehouse counts; the full warehouse was not re-probed, and the encoder
  constant does not vary by build.
- **Revision, 2026-08-26, the day of the override.** §2 and §5 were revised the
  same day, after reading the Pathling encoder source and probing NDJSON→Delta
  directly. Two changes. The cause is now pinned to a named compile-time constant
  rather than described as "a fixed encoder constant", and it is established that
  `step1_ndjson_to_delta.py` had no lever to pull — the question that prompted the
  reading was whether this was a missed configuration in our own build, and it is
  not. The counts `44,152` rate rows and `0/10,340` `mcg/kg/min` were corrected to
  `11,038` and `0/2,585`: the originals came from a `**/*.parquet` glob that reads
  every Delta file version rather than the current snapshot, and were uniformly 4×
  too high. **No conclusion changes** — the ratios are identical and
  `max(value_scale)` is 6 either way. The inflated figures are quoted in this
  concept's `state.json` justification, which is immutable; this note stands
  against it. `MIMIC_NOTES.md` is corrected at the entry itself.
