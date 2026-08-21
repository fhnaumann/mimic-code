# `gcs` — decision on `BLOCKED_REPRESENTATION`

- **Written:** 2026-08-21
- **Status at writing:** `BLOCKED_REPRESENTATION`, `concepts/measurement/gcs/attempt_0005`
- **Decision:** reopen and re-port emitting typed NULL, then accept the resulting
  gap. **Not** an override of `attempt_0005`.
- **Transitions:** `BLOCKED_REPRESENTATION → RUNNING` (today);
  `→ COMPLETED_WITH_DIVERGENCE` after `attempt_0006` earns it
- **Canonical SQL:** `mimic-iv/concepts/measurement/gcs.sql`
- **Fidelity (attempt_0005):** 1,061,579 / 1,637,763 identical (64.8188%)
- **Upstream issue:** kind-lab/mimic-fhir#125

> **This file is written before the override it describes.** The README asks for
> one file per override written when the override is applied; this one is written
> at the reopen, because the reopen is the load-bearing decision and the
> acceptance follows mechanically from it. Every `attempt_0005` figure below is
> copied from an artifact. Every **variant B** figure is a *probe projection*
> from Slurm job 30309450, explicitly labelled as such, and must be restated from
> `attempt_0006/comparison.full.json` before `accept-divergence` is run. See §7.

## 1. The problem

MIMIC-on-FHIR cannot distinguish `No Response-ETT` (patient intubated, cannot
speak) from `No Response` (patient unresponsive) on GCS verbal-response
observations. Both source rows carry `valuenum = 1` and both are served as
`valueQuantity = 1`. On full data 644,776 of 1,627,786 itemid-223900 rows are
ambiguous this way — 573,198 `No Response-ETT` and 71,578 `No Response`
(`/scratch3/nau025/debug-chartevents-value-drop/results/job-29804685/gcs_verbal_223900.csv`).
The canonical SQL branches on that exact text at `gcs.sql:33` and `gcs.sql:45`,
so the loss reaches `gcs_verbal`, `gcs_unable`, total `gcs`, and the six-hour
carry-forward.

The equivalence judge blocked the concept on `attempt_0005`
(`attempt_0005/evidence/equivalence-judge.md`, restated in
`state/gcs/state.json:error_message`):

> "essential upstream representation loss at
> `mimic-fhir/sql/fhir_observation_chartevents.sql:69-80` discards the No
> Response-ETT discriminator, conflating it with No Response as Quantity 1. This
> changes gcs, gcs_verbal, gcs_unable, total GCS and six-hour carry-forward;
> 576086 differing_conflict rows plus 74 only_candidate and 98 only_oracle were
> observed (64.82% identical). Resource IDs are opaque and cannot recover the
> label."

**Every word of that is upheld.** This entry rejects nothing in the judge's
finding. What it rejects is that `blocked` remains the right terminal state once
the port stops *stating a value it does not have*. The judge ruled on a port that
serves `gcs = 10` where the truth is `15`, with nothing marking the row; its
stated reason for blocking is that publishing such a table "would conceal
semantic ambiguity" (`attempt_0005/evidence/equivalence-judge.md`). A port that
emits typed NULL on those rows conceals nothing — the absence is the marking. So
the remedy is the row-level typed NULL of `LOOP_CONTRACT.md:406-411`, not a
block, and that requires a new attempt rather than an override of this one.

## 2. What caused it

`mimic-fhir/sql/fhir_observation_chartevents.sql:69-80`:

```sql
, 'valueQuantity',
    CASE WHEN ce_VALUENUM IS NOT NULL THEN
        jsonb_build_object(
            'value', ce_VALUENUM
            , 'unit', ce_VALUEUOM
            , 'system', 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units'
            , 'code', ce_VALUEUOM
    ) ELSE NULL END
, 'valueString',
    CASE WHEN ce_VALUENUM IS NULL THEN
        ce_VALUE
    ELSE NULL END
```

`ce_VALUENUM IS NOT NULL` and `ce_VALUENUM IS NULL` partition the rows, so
exactly one element is ever written. `ce.value` survives **only** where there is
no number — precisely where it adds nothing to the number. Itemid 223900 has
`valuenum` on 1,627,786 of 1,627,786 rows
(`.../job-29804685/concept_itemid_audit.csv`, `text_survives_etl = False`), so
its text is discarded unconditionally.

**No-alternative-carrier check.** Every element that could have carried the
discriminator, and why it does not:

| Carrier | Verdict |
|---|---|
| `Observation.valueString` | Never written for 223900 — the branch above is mutually exclusive with `valueQuantity`, and `valuenum` is always present. |
| `Observation.valueCodeableConcept` | Not written by this ETL at all. |
| `Observation.dataAbsentReason` | Not written by this ETL at all. |
| `Observation.code` | Carries the itemid only (`223900`), identical for both labels. |
| `Observation.component` | Not written by this ETL. This is the element the fix should use (§5). |
| `Observation.id` | A UUIDv5 seeded on `ce.value` (`:20-21`), so the label is *technically* brute-forceable. Forbidden opaque-identity inversion; removed by human reopen twice (`state/gcs/state.json:reopen_history`). Not a carrier. |
| `oxygen_delivery` (itemid 226732) | Text **does** survive — 1,536,870 rows, zero `valuenum`. But it has 553 `Endotracheal tube` rows and 41,112 invasive-device rows against 573,198 ETT verbal rows. Measured as a substitute discriminator: **4.7% recall, 14.0% accuracy** (job 30309569). No discriminating power. |
| `ventilation` / `ventilator_setting` | The strong signal, and unavailable: `ventilator_setting` is itself `BLOCKED_REPRESENTATION` on **this same statement**, 652,532 rows of mode/type text discarded (`state/ventilator_setting/state.json`). Measured at its oracle-perfect upper bound it reaches only 80.1% accuracy / 82.8% recall with 29,924 false positives (job 30309569) — an estimate, not a mapping, even if it were buildable. |

The same statement destroys both the discriminator and the only witness that
could have replaced it. Nothing served today recovers it, by any query.

## 3. Intentional or a bug?

Ruled per class. One statement produces losses of several kinds and they do not
share a grade.

| # | Class | Scope | Grade |
|---|---|---|---|
| a | `value[x]` exclusivity — `valueQuantity` and `valueString` cannot both be set | the element itself | **Inherent** |
| b | Not carrying the source text in `Observation.component` instead | 1,627,786 rows (itemid 223900) | **Bug** |
| c | Same omission, ventilator mode/type text | 652,532 rows (`ventilator_setting`) | **Bug** |
| d | Text that is only a rendering of the number | remainder of chartevents | **Not loss** |
| e | `TIMESTAMPTZ` DST normalisation at `:9,67` | 74 paired key shifts, 24 residual | **Repairable defect, already `accept`** |

**(a) is inherent and that is not a hedge.** `Observation.value[x]` is a FHIR
choice type; populating both variants is non-conformant. Upstream's exclusivity
at `:69-80` is *forced by the spec*, not chosen. Any entry that convicts the
exclusivity itself as a bug is wrong on FHIR.

**(b) is a bug for a reason that does not touch (a).** `Observation.component` is
a separate `0..*` element; carrying the verbatim text there is conformant and
purely additive. And the ETL already treats `ce.value` as identity-bearing —
twelve lines above the branch that discards it, at `:20-21`, it seeds the
resource UUID with it:

```sql
-- chartevents uuid dependent on 'value' to be unique (stay_id and itemid should be enough but a couple cases break this)
, uuid_generate_v5(ns_observation_ce.uuid, ce.stay_id || '-' || ce.charttime || '-' || ce.itemid || '-' || ce.value) AS uuid_CHARTEVENTS
```

Asserting that a field distinguishes rows and then declining to serve it is
self-inconsistent, and it produces pairs of Observations with distinct ids and
byte-identical content.

**Trap check (`human_override/README.md`).** The argument convicting (b) —
"a conformant, additive element was available" — applies verbatim to (c), and (c)
is graded identically rather than being waved through as inherent because it sits
in a different concept. The middle tier the README warns about is real here and it
is (a): a genuine spec constraint that would otherwise be used to excuse (b). The
split is deliberate. Nothing in this table is graded inherent on the strength of
an argument that convicts something else in it.

**Which way this cuts.** Grading (b) and (c) as repairable *strengthens* the
acceptance: `LOOP_CONTRACT.md:256-315` makes an acknowledged, repairable
`mimic-fhir` defect the archetype for accept-rather-than-block. Filed upstream as
kind-lab/mimic-fhir#125.

## 4. Example of the loss

From `attempt_0005/comparison.full.json` → `diff.samples.differing_conflict[0]`:

| column | oracle | port (`attempt_0005`) |
|---|---|---|
| `subject_id` | 18730522 | 18730522 |
| `stay_id` | 30004391 | 30004391 |
| `charttime` | 2153-09-07T12:00:00 | 2153-09-07T12:00:00 |
| `gcs_eyes` | 3.0 | 3.0 |
| `gcs_motor` | 6.0 | 6.0 |
| `gcs_verbal` | **0.0** | **1.0** |
| `gcs_unable` | **1** | **0** |
| `gcs` | **15.0** | **10.0** |

The served resource that explains it: the `Observation` for itemid 223900 at that
`stay_id`/`charttime` carries `valueQuantity.value = 1` with `valueString` absent.
Relational MIMIC-IV holds `value = 'No Response-ETT'`, `valuenum = 1`. The port
reads the `1`, scores verbal as `1` instead of the sentinel `0`, so
`gcs.sql:45`'s `endotrachflag` never fires and `gcs.sql:70-71`'s "replace GCS
during sedation with 15" branch is never taken. The eyes and motor components —
which FHIR carries perfectly — are correct on this row; the total is wrong
anyway.

## 5. What a fix would look like

§3 calls (b) and (c) fixable. Filed as kind-lab/mimic-fhir#125. Patch
`fhir_observation_chartevents.sql:69-80` to keep `valueQuantity` primary and add
the verbatim source text as a component, leaving `value[x]` conformant:

```sql
, 'valueQuantity',
    CASE WHEN ce_VALUENUM IS NOT NULL THEN
        jsonb_build_object(
            'value', ce_VALUENUM
            , 'unit', ce_VALUEUOM
            , 'system', 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-units'
            , 'code', ce_VALUEUOM
    ) ELSE NULL END
, 'valueString',
    CASE WHEN ce_VALUENUM IS NULL THEN ce_VALUE ELSE NULL END
-- NEW: the source text, whenever it is not merely a rendering of the number
, 'component',
    CASE WHEN ce_VALUENUM IS NOT NULL AND ce_VALUE IS NOT NULL
              AND ce_VALUE !~ '^\s*-?[0-9]*\.?[0-9]+\s*$' THEN
        jsonb_build_array(jsonb_build_object(
            'code', jsonb_build_object('coding', jsonb_build_array(jsonb_build_object(
                 'system', 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-observation-component'
               , 'code', 'sourceValue')))
          , 'valueString', ce_VALUE
    )) ELSE NULL END
```

The §4 row re-served under it gains
`component[0].code.coding.code = 'sourceValue'`, `component[0].valueString =
'No Response-ETT'`. The port then reads the discriminator from that component
instead of the lost `value`, `gcs.sql:33,45` fire as written, and the row it
produces is `gcs_verbal = 0.0`, `gcs_unable = 1`, `gcs = 15.0` — exact match to
the oracle. The same patch unblocks `ventilator_setting` (class c) with no
further change.

## 6. Numbers

**`attempt_0005` — the blocked port (variant A).** All from
`attempt_0005/comparison.full.json`.

| figure | value | fraction |
|---|---|---|
| oracle rows | 1,637,763 | — |
| `diff.identical` | 1,061,579 | 1,061,579 / 1,637,763 = 64.8188% |
| `diff.differing_conflict` | 576,086 | 576,086 / 1,637,763 = 35.1752% |
| `diff.columns_conflicting.gcs` | 576,086 | 576,086 / 1,637,763 |
| `diff.columns_conflicting.gcs_verbal` | 575,877 | 575,877 / 1,637,763 |
| `diff.columns_conflicting.gcs_unable` | 573,170 | 573,170 / 1,637,763 |
| `diff.differing_null_only` | 0 | — |
| `diff.only_candidate` | 74 | class (e) |
| `diff.only_oracle` | 98 | 74 class (e), 24 residual |

Per-column NULL counts under variant A: **zero**. That is the defect — the port
has no absent values, only wrong ones.

**By §3 class.** Class (b) accounts for 576,086 / 576,086 of the conflict —
the whole of it. Class (e) accounts for the 74 `only_candidate` and 74 of the 98
`only_oracle`, with 24 residual (`diff.key_attribution`), and is not this entry's
subject.

**Variant B — the projection. Probe figures, not artifact figures.** From
`/scratch3/nau025/gcs-blast-radius/results/job-30309450/summary.json`. The probe
simulates the FHIR loss on relational MIMIC-IV; its §0 validates that simulation
against `attempt_0005/candidate.full.parquet` at `gcs_disagree = 0`,
`verbal_disagree = 0`, `unable_disagree = 0` over 1,637,665 joined rows, and
reproduces the recorded split to within 98 rows (the `only_oracle` rows the
comparator drops and the probe pairs).

| figure | variant A | **variant B** |
|---|---|---|
| rows with a **wrong** `gcs` | 576,114 | **0** |
| rows with NULL `gcs` | 0 | 678,748 / 1,637,763 = 41.4436% |
| rows exact | 1,061,649 | 959,015 / 1,637,763 = 58.5564% |
| `gcs_unable` NULL | 0 | 1,637,763 / 1,637,763 = 100% |
| mean signed error on differing rows | −7.129 | — (no values stated) |
| error range | −12 … 0 | — |

The NULL predicate is `ambiguous OR ambiguousprev`: an itemid-223900 observation
served as Quantity 1 at this `charttime`, or at the previous one inside the
six-hour window. 678,748 NULLed rows against 644,776 ambiguous `(stay_id,
charttime)` groups — the 33,972 difference is carry-forward reach.

`gcs_verbal`'s NULL count under B was not separately measured and **must be
restated from `attempt_0006/comparison.full.json`**; it follows the same
predicate as `gcs`.

**Post-fix projection (§5 landed).** The port produces 1,637,763 / 1,637,763
exact, less the class (e) DST residual of 24 `only_oracle` — i.e. 1,637,739
matched exact, with the residual ruled on its own merits as
`LOOP_CONTRACT.md:315` requires.

## 7. Misc

- **Essential-loss test (`LOOP_CONTRACT.md:481`) applied to variant B, term by
  term.** *Row inclusion:* unchanged — 1,637,763 in, 1,637,763 out; the 74/98
  unpaired rows are class (e), not this loss. *Semantic grain:* unchanged —
  `(stay_id, charttime)` still identifies one row of this concept. *Grouping:*
  the concept's `GROUP BY ce.subject_id, ce.stay_id, ce.charttime` is upstream of
  the NULL and unaffected. *Temporal carry-forward:* **affected** — the NULL
  propagates through `COALESCE(gcsverbal, gcsverbalprev)`, which is why the NULL
  predicate includes `ambiguousprev` rather than pretending it does not. *
  Contamination of representable values:* **affected at the dependent level, and
  this is the condition below** — measured 4,645 stays where `first_day_gcs`'s
  `MIN` falls through a NULLed row to a higher survivor, mean signed error +4.873
  (job 30309450, `first_day_gcs.B_typed_null`). Two of five terms are touched.
  This is a weaker pass than `antibiotic`'s, and it is accepted only because the
  alternative on offer states 576,086 wrong values instead.
- **Condition of acceptance.** Dependents must propagate the NULL, not skip it:
  where any row in the aggregation window is NULL, emit NULL rather than `MIN`
  over survivors. That converts the 4,645 contaminated stays into visible
  absences and satisfies `LOOP_CONTRACT.md:905-911`'s "the gap stays visible at
  every level". Without it the fifth term above is not met and this entry does
  not carry.
- **Declaration mechanics.** `gcs_unable` is 100% NULL under B and belongs in
  `unrepresentable.json`. `gcs` and `gcs_verbal` are ~41% NULL and must **not**
  be declared — a partial declaration is a blocking
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:439-443`). They are
  stated in the attempt's justification and the comparator reports them as the
  `differing_null_only` they are (`LOOP_CONTRACT.md:421-423`).
- **No marker column.** Shape is total (`LOOP_CONTRACT.md:425`), so a
  suspect-row flag cannot be added to the table. Under variant A the damaged rows
  are inferable via `gcs_verbal = 1` — measured 99.986% row-level recall, 82 of
  576,114 missed, but **100% recall at stay level**, `CLEAN_BUT_WRONG = 0`, with
  41,038 / 72,718 stays provably clean (job 30309450, `marker_*`). Under variant
  B no inference is needed: the NULL is the marker, structurally. That asymmetry
  is a further argument for B.
- **Consistency with siblings.** `ventilator_setting` is `BLOCKED_REPRESENTATION`
  on the identical statement (class c). It should be reopened under the same
  reasoning or the two verdicts contradict each other; `LOOP_CONTRACT.md:512-516`
  rules against splitting identical concepts on which column the builder reached
  first. `rrt` (225965), `crrt` (224146) and `code_status` (223758) are **not**
  affected — all three have zero `valuenum`, so their text is served as
  `valueString` (`.../job-29804685/concept_itemid_audit.csv`). This defect reaches
  two concepts, not four.
- **Consistency with earlier verdicts.** `antibiotic` and `nsaid` accepted gaps
  that were typed NULL, changed no computed value, and contaminated nothing. This
  is the first accepted gap in the loop that reaches temporal carry-forward, and
  the entry says so rather than assimilating it to the earlier two.
- **Downstream.** Seven concepts read `gcs` or `first_day_gcs`:
  `firstday/first_day_gcs.sql`, `firstday/first_day_sofa.sql`, `score/sofa.sql`,
  `score/sapsii.sql`, `score/oasis.sql`, `score/lods.sql`, `score/apsiii.sql`,
  and `sepsis/sepsis3.sql` transitively. Per `LOOP_CONTRACT.md:929-950` their
  divergence is wholly inherited: they cite this acceptance, are not re-blocked,
  and must not report these rows as their own conflict. Accepting `gcs` is a
  decision about `gcs` *and every concept that reads it* — that is the whole of
  what is being decided here, and it is why the reopen precedes the acceptance.
- **Caveats.** (i) Every variant-B figure in §6 is a probe projection and must be
  restated from `attempt_0006/comparison.full.json` before `accept-divergence`
  runs. (ii) The probe's SOFA rebuild disagrees with the shipped
  `mimiciv_derived.sofa` on 8,935 of 6,043,902 rows (0.148%), a `ROWS BETWEEN 23
  PRECEDING` approximation of the trailing-24h window; downstream SOFA figures
  carry that error bar. (iii) The judge is not re-called on `attempt_0005`; if
  `attempt_0006` earns `accept` on its own as a `gap_shaped` review, no human
  override is needed and the result is the stronger one — see the command note.
- **Revisions.** None. First version, 2026-08-21.

---

# 2026-08-21 — override applied, on `attempt_0006`

**Supersedes §6's variant-B projections** (probe job 30309450) with the figures
`attempt_0006/comparison.full.json` actually recorded, and completes the header:
the transition applied is `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`,
`--by human`, on `concepts/measurement/gcs/attempt_0006`. Sections 1–5 stand
unaltered; §2's causal account and §3's grading are unchanged by the re-port,
because the re-port changed the *port*, not the upstream statement.

## What `attempt_0006` produced

The reopen did what it was asked to. Every mechanical objection to
`attempt_0005` is gone:

| axis | `attempt_0005` | `attempt_0006` |
|---|---|---|
| `divergence.blocking` | 2 classes (74 `only_candidate`, 576,086 `differing_conflict`) | **`[]` — empty** |
| `diff.differing_conflict` | 576,086 | **0** |
| `diff.differing_null_only` | 0 | 1,637,665 |
| `divergence.tier` | `contested` | **`gap_shaped`** |
| `unrepresentable.json` | absent | `gcs_unable`, **confirmed** by the comparator (`diff.excluded_as_unrepresentable = ['gcs_unable']`) |
| `key_attribution.complete` | `False`, 24 residual `only_oracle` | **`True`, residual 0 on both sides** |
| rows stating a wrong value | 576,086 | **0** |

Recorded figures, all from `attempt_0006/comparison.full.json`:

| figure | value | fraction |
|---|---|---|
| oracle rows | 1,637,763 | — |
| candidate rows | 1,637,739 | difference is the 98/74 DST key split |
| `diff.identical_representable` | 958,951 | 958,951 / 1,637,763 = 58.5525% |
| `diff.differing_null_only` | 1,637,665 | 1,637,665 / 1,637,763 = 99.9940% |
| `diff.differing_conflict` | 0 | — |
| `columns_differing.gcs` | 678,714 | 678,714 / 1,637,763 = 41.4415% |
| `columns_differing.gcs_verbal` | 678,714 | 678,714 / 1,637,763 = 41.4415% |
| `columns_differing.gcs_unable` | 1,637,665 | declared, excluded |
| `diff.identical` | 0 | artefact of the declared all-NULL column, not a fidelity claim |

**The probe was accurate.** §6 projected 678,748 NULL `gcs` rows and 959,015
identical-representable; the artifact records 678,714 and 958,951 — 34 and 64
rows low, both inside the 98-row DST key split the probe pairs and the
comparator does not. §6's projections are superseded by these, not corrected in
substance.

## What the judge ruled, and what is being rejected

`attempt_0006/evidence/equivalence-judge.md` returned `blocked` again:

> "The loss is essential, not ancillary: canonical `gcs.sql:33-45,62-95,101-125`
> uses it for `gcs_verbal`, `gcs_unable`, total `gcs`, and immediate-previous
> six-hour carry-forward. Attempt 0006 therefore has typed NULL `gcs` and
> `gcs_verbal` on 678,714 rows and typed NULL `gcs_unable` on all rows; this
> cannot be published as a faithful core GCS table."

**The judge is not mistaken, and this override does not claim it is.** It read
the artifact correctly — it explicitly noted "0 total identical because of the
declared column" rather than reporting that 0% as catastrophic fidelity, so the
trap at `LOOP_CONTRACT.md:469-472` was not hit. And it applied
`LOOP_CONTRACT.md:481` as written: the absence does reach temporal carry-forward
and does leave a clinically meaningful derived output absent. On the rule as
stated, `blocked` follows.

What is rejected is the **remedy**, not the finding. `:481` prescribes `blocked`
so that a concept does not "publish a plausible-looking table after an input
needed by the core derivation has been lost" — the harm it names is a table
"whose ordinary values conceal that ambiguity". `attempt_0006` conceals nothing:
it states no value it does not have, on any row, and the one column that is
wholly underivable is declared and comparator-verified. The rule's remedy is
aimed at a failure mode this port does not exhibit, and applying it here
withholds 958,951 exactly-correct rows to prevent a concealment that is not
occurring. That is a judgement about whether the rule's purpose is served, which
is not the judge's to make against a human — `LOOP_CONTRACT.md:777-780` reserves
it explicitly.

The `gap_shaped` bar the judge was set is met on its own terms
(`divergence.judge_bar`): the FHIR element that does not exist is named
(`Observation.component`, §2), it explains the magnitude and shape exactly
(678,714 NULL rows = the `ambiguous OR ambiguousprev` predicate, and 100% NULL
`gcs_unable`), and "every defensible mapping was tried" is **measured** rather
than asserted — `oxygen_delivery` at 4.7% recall and the oracle `ventilation`
table at 80.1% accuracy, both in §2, from job 30309569.

## Essential-loss re-test, on `attempt_0006`

Restating §7 against the recorded artifact rather than the projection:

| `:481` term | verdict |
|---|---|
| row inclusion | **unchanged** — 1,637,763 oracle rows, 1,637,739 candidate; the 98/74 split is fully attributed to the DST cast, `residual 0` both sides, `key_attribution.complete = True` |
| semantic grain | **unchanged** — `(stay_id, charttime)` still identifies one row |
| grouping | **unaffected** — upstream of the NULL |
| temporal carry-forward | **reached** — the NULL propagates through `COALESCE(gcsverbal, gcsverbalprev)`; the predicate includes `ambiguousprev` rather than pretending otherwise |
| contamination of representable values | **not in this table** — `differing_conflict = 0`, `blocking = []`. Reached at the *dependent* level only, and the condition below is what holds it |

Two of five terms touched, one of them only downstream and only if the condition
is not honoured. `attempt_0005` touched the fifth term inside this table itself,
on 576,086 rows. That is the difference the override rests on.

## Conditions carried by this acceptance

1. **Dependents propagate the NULL through `MIN`.** Where any row in the
   aggregation window is NULL, emit NULL rather than the minimum over survivors.
   Unhonoured, this reintroduces 4,645 silently-wrong stays at `first_day_gcs`
   (job 30309450, `first_day_gcs.B_typed_null.WRONG_VALUE`), which is the fifth
   `:481` term reappearing one level down. This is a condition, not a suggestion.
2. **`ventilator_setting` is revisited under the same reasoning** — same
   statement, graded identically in §3(c). Leaving it blocked while `gcs` is
   accepted makes the two verdicts contradict.
3. **The acceptance is re-derivable, not permanent.** When
   kind-lab/mimic-fhir#125 lands, `gcs` should be reopened; §5 projects exact
   rows from the same SQL, and the override then costs nothing to discard.

## What this is worth

Stated plainly, because `LOOP_CONTRACT.md:806-812` requires it: this is a human
override and a weaker result than a judge acceptance. `status` reports it on the
"K/65 divergence accepted by a human (manual override)" line, never summed with
the exact-match or judge-accepted counts. The table it ships is NULL on 41.44% of
rows for `gcs` and `gcs_verbal` and 100% NULL for `gcs_unable`. A reader who
needs core GCS on intubated patients should not use it; a reader who needs the
58.55% it does carry can, and can see exactly which rows those are.

**Revisions.** Section added 2026-08-21, superseding §6's projections with
`attempt_0006` artifact figures. §§1–5 unaltered.
