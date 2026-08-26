# `vitalsign` — human override out of `BLOCKED_REPRESENTATION`

- **Applied:** 2026-08-25 06:20 UTC
- **Transition:** `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, `--by human`
- **Attempt:** `concepts/measurement/vitalsign/attempt_0003`
- **Canonical SQL:** `mimic-iv/concepts/measurement/vitalsign.sql`
- **Fidelity:** 9,745,499 / 9,745,500 identical (99.99999%), one oracle row unmatched

> **Backfill, written 2026-08-26.** This entry was reconstructed the day after the
> ruling, from `state/vitalsign/state.json`, the three attempts' artifacts,
> `MIMIC_NOTES.d/vitalsign.md`, and the cited ETL — not at the time the override
> was applied, as the folder's rules require. Nothing in it is new reasoning: the
> `state.json` justification paragraph is the contemporaneous record and this file
> expands it into the seven sections. Where this entry adds anything the
> justification did not say, §7 marks it as such.

## 1. The problem

Exactly **one** of 9,745,500 oracle rows has no counterpart in the port:
`(stay_id = 34934165, charttime = 2151-10-03 05:14:00)`, an ICU glucose reading of
96 mg/dL. There is nothing else. Zero `only_candidate`, zero conflicts, zero
NULL-only differences, no unrepresentable declarations, no divergent dependencies.
The tier is `gap_shaped`.

The equivalence judge blocked it
(`attempt_0003/evidence/equivalence-judge.md`):

> This is essential loss because it changes row inclusion and the clinically
> meaningful vital-sign table grain, despite its size.

Every factual finding in that verdict is confirmed, including that the candidate
had exhausted the defensible mappings. What is rejected is the conclusion. "It
changes row inclusion" is true of any absent row whatsoever, so as stated the test
has no threshold and one row fails it exactly as a million would. §7 applies the
essential-loss test of `LOOP_CONTRACT.md:481` term by term instead.

## 2. What caused it

`mimic-fhir/sql/fhir_observation_chartevents.sql:35-37` — a hard-coded exclusion
of one `(stay_id, charttime)` tuple, applied in the `WHERE` clause of the CTE that
feeds the insert, so the rows never become Observations at all:

```sql
        -- filter out the one duplicate value (one patient at one charttime)
        ((stay_id = 34934165) AND (charttime = '2151-10-03 05:14:00.000')) = FALSE
        AND value IS NOT NULL -- one value in the whole TABLE
```

The upstream intent is visible in the comment: two source rows at that tuple are
duplicates, and rather than deduplicate them the ETL drops the tuple. A full-oracle
probe during attempt_0001 confirmed the shape — two identical itemid `220621` rows
at that tuple (`subject_id = 13793458`, `value = '96'`, `valuenum = 96`)
(`MIMIC_NOTES.d/vitalsign.md`).

No alternative carrier, because nothing is created: there is no Observation with
that code, effective time, encounter, or value at that tuple. `Patient`,
`Encounter`, `issued`, `component` and opaque resource identity were all checked by
the judge and carry nothing. This is an **absence of a resource**, not an
unpopulated element on a resource that exists — which is why no query recovers it
and why `unrepresentable.json` is the wrong instrument (§7).

## 3. Intentional or a bug?

One statement, one class — unusually simple for this folder.

| class | what is lost | verdict |
|---|---|---|
| 1 | every chartevents row at `(34934165, 2151-10-03 05:14:00)`, and therefore the whole derived group | **bug** — the response to a duplicate is to deduplicate, not to drop the tuple |

It is graded a bug rather than a defensible judgement, and the distinction from
`nsaid`/`antibiotic` tier 2 is worth stating. There, the source value was
*corrupt* (`start > stop`) and upstream could not tell which of the two endpoints
to trust, so declining to guess was defensible. Here the two source rows are
**identical** — same itemid, same `value`, same `valuenum`. There is nothing to
adjudicate and no guess to make; either row, taken alone, is the correct answer,
and `SELECT DISTINCT` or a `GROUP BY` would have produced it. The exclusion also
overshoots its own justification: it drops the *entire tuple* for *all itemids*,
not just the duplicated `220621` pair.

Per `human_override/README.md`, grading it *repairable* strengthens this entry
rather than weakening it (`LOOP_CONTRACT.md:256-315`). The override rests on §2
and §7 — nothing recoverable from what is served today, and an absence that
reaches nothing essential.

## 4. Example of the loss

The only affected row, from `attempt_0003/comparison.full.json`
(`diff.samples.only_oracle`, which is a one-element list):

| | `stay_id` | `charttime` | `glucose` | all other columns |
|---|---|---|---|---|
| **relational MIMIC-IV (oracle)** | 34934165 | `2151-10-03 05:14:00` | 96 | NULL |
| **port over MIMIC-on-FHIR** | — | — | *row absent* | — |

Canonical `vitalsign.sql:68-71` selects itemid `220621` into `glucose` via
`AVG(CASE WHEN itemid IN (225664, 220621, 226537) AND valuenum > 0 THEN valuenum END)`,
and the surrounding `GROUP BY subject_id, stay_id, charttime` collapses the two
duplicate source rows into a single `glucose = 96` row. So exactly one oracle row
depends on the excluded tuple, and exactly one is missing. The served data holds no
Observation at that tuple to build it from.

## 5. What a fix would look like

Deduplicate instead of excluding. Drop the hard-coded predicate and let the
duplicate collapse where duplicates are actually a problem:

```sql
    WHERE
        value IS NOT NULL -- one value in the whole TABLE
```

with the source CTE selecting `DISTINCT` over the identity-bearing columns (or
the UUID calculation keyed so the two identical rows generate one resource, which
they already would — the pair differs in no column the UUID reads, which is the
likely reason the tuple was excluded rather than deduplicated in the first place).

Under that fix the §4 row would serve as one Observation with code `220621`,
`effectiveDateTime 2151-10-03T05:14:00`, `valueQuantity 96 mg/dL`, and the port —
unchanged, no edit to `concept.sql` — would emit `glucose = 96` at
`(34934165, 2151-10-03 05:14:00)`. Fidelity would be 9,745,500 / 9,745,500, exact.

This is a genuine `mimic-fhir` PR: three lines, one tuple, no IG change, no
profile change. **It was not in the 2026-08-21 fix wave** and remains open.

## 6. Numbers

From the three full comparisons. The 2026-08-24 rebuild is visible in the jump
from attempt_0002 to attempt_0003, with the *same* `concept.sql`:

| | attempt_0001 | attempt_0002 | **attempt_0003** |
|---|---|---|---|
| identical | 9,743,636 | 9,743,636 | **9,745,499** |
| `only_oracle` | 1,106 | 1,106 | **1** |
| `only_candidate` | 343 | 343 | **0** |
| `differing_conflict` | 758 | 758 | **0** |
| `differing_null_only` | 0 | 0 | **0** |
| tier | `contested` | `contested` | **`gap_shaped`** |

All 2,207 DST-attributed divergences cleared. Attempt_0003 residual: **1 row of
9,745,500 = 0.0000103%**, fidelity 0.99999990. Key `(stay_id, charttime)`,
classification `keyed`, no `excluded_as_unrepresentable` columns. Comparator
tolerances: relative 0.001, absolute 1e-9, timestamps 1 s, row count exact.

By the §3 classes: class 1 accounts for the single row; there are no other classes.

**Post-fix projection** (§5 applied upstream): `only_oracle` 0, fidelity
9,745,500 / 9,745,500 = 1.000000, tier `match`.

## 7. Misc

- **Why the loss is acceptable** (`LOOP_CONTRACT.md:481`), term by term. *Row
  inclusion:* changed, by one row of 9,745,500 — this is the term the judge
  invoked and the only one that moves. The change is not a systematic inclusion
  rule; it is one tuple named as a literal in the ETL, affecting one ICU stay at
  one minute. *Semantic grain:* unchanged — keyed 1:1 on `(stay_id, charttime)`,
  zero `only_candidate`, and the surviving 9,745,499 rows are grouped exactly as
  the oracle groups them. *Grouping:* unchanged — no group is partially
  reproduced; the affected group is absent whole, which is the honest shape.
  *Temporal carry-forward:* `vitalsign.sql` has no window and no carry-forward, so
  the absence cannot propagate along time within the concept. *Contamination of
  representable values:* none — no estimate stands in for the missing row, and
  every one of the 9,745,499 present rows is exact.
- **Not a declaration.** `unrepresentable.json` declares a *column* 100% NULL. The
  loss here is a whole row, and every column is populated on every row that
  exists, so the comparator would reject a declaration as
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:420-423,440-446`).
- **What downstream inherits.** `first_day_vitalsign` and every APSIII / SOFA /
  OASIS path that reads `vitalsign` carry this one-row absence for stay 34934165.
  Their judges must be told (`LOOP_CONTRACT.md:988-1000`), and a dependent that
  reports that stay as its own conflict has misattributed it. In practice the
  absence is a single glucose reading at a single minute, and `glucose` is not a
  SOFA, APSIII or OASIS input, so the expected downstream footprint is zero rows —
  but "expected" is doing work in that sentence and it has not been measured.
- **The judge's test, stated fairly.** The verdict is not unreasonable on its face:
  a missing row *is* categorically worse than a NULL cell, because it is invisible
  to a consumer who does not have the oracle. That is why §4 names the row and
  this file exists. The override says that one named, reproducible, upstream-caused
  absence of 9.7 million is a documented divergence, not a disqualification — and
  that a test which cannot distinguish one row from a million is not a test.
- **Consistency with sibling concepts.** No sibling shares this exclusion, because
  it is a literal tuple rather than a rule. Its nearest relatives in this folder
  are `antibiotic` and `nsaid`, both accepted at 4-8% loss where this is
  0.00001%.
- **Added by this backfill, not in the contemporaneous justification** (§3's
  bug-vs-defensible grading and its contrast with the `nsaid` tier 2 reasoning;
  §5's concrete patch and post-fix projection; the term-by-term essential-loss
  walk above; the downstream-footprint caveat). The `state.json` paragraph
  asserted the ruling and its evidence; it did not argue the grading. No number
  here is new — every figure is copied from the artifacts named in §6.
