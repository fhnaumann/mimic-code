# `ventilator_setting` — review of `BLOCKED_REPRESENTATION`, block **upheld**

- **Written:** 2026-08-21
- **Status at writing:** `BLOCKED_REPRESENTATION`,
  `concepts/measurement/ventilator_setting/attempt_0001`
- **Decision:** the block **stands**. Its *stated reason* is replaced.
- **Transition applied:** **none.** No `accept-divergence`, no `retry`, no
  `reopen`. `state.json` is unchanged except for `error_message` (§7).
- **Canonical SQL:** `mimic-iv/concepts/measurement/ventilator_setting.sql`
- **Fidelity (attempt_0001):** 353,556 / 1,006,127 identical (35.1403%)
- **Upstream issue:** kind-lab/mimic-fhir#125
- **Probe:** Slurm job 30314398,
  `/scratch3/nau025/vent-blast-radius/results/job-30314398/`

> **This file is not an override.** It is filed here anyway because
> `human_override/` is where a human's ruling on a judge's verdict lives, and
> "we looked again and the block is still right, for different reasons" is such
> a ruling. See `README.md` §"Entries that uphold a block" for the shape delta.
> It exists because `human_override/gcs.md` carries a standing condition —
> "`ventilator_setting` is revisited under the same reasoning" — and a reader who
> finds that condition needs to be able to find how it was discharged.
>
> Every `attempt_0001` figure is copied from `comparison.full.json`. Every
> figure labelled **probe** is from job 30314398 and is a relational simulation
> of the FHIR loss, validated against the artifact in §6 before use.

## 1. The problem

`ventilator_setting` pivots three columns out of `chartevents.value` text —
`ventilator_mode` (itemid 223849), `ventilator_mode_hamilton` (229314) and
`ventilator_type` (223848) — at `ventilator_setting.sql:87-91`. MIMIC-on-FHIR
discards that text wherever the row also carries a number, so the port serves
typed NULL on 652,532 of 1,006,127 rows.

The equivalence judge blocked the concept on `attempt_0001`
(`attempt_0001/evidence/equivalence-judge.md`, restated in
`state/ventilator_setting/state.json:error_message`):

> "the missing ventilator mode/type text is essential to clinically meaningful
> ventilation classification and temporal carry-forward in
> `mimic-iv/concepts/measurement/ventilation.sql:36,55-127,171-180`. Fidelity was
> 353,556/1,006,127 identical (35.14%), with no unrepresentable exclusion."

**The verdict is upheld. The reason is not.** The judge's premise is that the
mode text is *lost*. It is not lost — it is **unlabelled**. Full data shows zero
ambiguous `(itemid, valuenum)` pairs on all three itemids (§2), so every distinct
ventilator mode remains a distinct served `valueQuantity`; only the human-readable
string is absent, and no served terminology supplies it. That is a materially
different finding from `gcs`, and it changes which argument the block rests on:

- The judge's ground — "essential text is gone" — **fails**, because a
  reconstruction exists that is exact on every row (§6, variant C).
- Two other grounds hold instead, and they are what this entry substitutes:
  (i) the reconstruction is not derivable from anything the IG serves, so
  `gap_shaped`'s "every defensible mapping was tried" cannot be met by asserting
  no mapping exists — one exists and works; and (ii) the absence, if accepted,
  **does not stay visible**: it converts into silently-low SOFA respiration
  scores on 22,291 stays (§7).

So this entry rejects the `gcs` parallel that `gcs.md` §7 assumed, and reaches
`gcs`'s conclusion anyway by a different route.

## 2. What caused it

`mimic-fhir/sql/fhir_observation_chartevents.sql:69-80` — the same statement as
`gcs`, verified against the local checkout at commit `69c2c28`:

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
`ce.value` survives only where there is no number. Unlike itemid 223900, these
three itemids are **split** across both branches — which is why the port recovers
part of each column and not none of it (probe, job 30314398):

| itemid | label | rows | Quantity branch (text dropped) | string branch (text kept) | labels dropped | labels kept |
|---:|---|---:|---:|---:|---:|---:|
| 223849 | Ventilator Mode | 443,254 | 423,932 | 19,322 | 23 | 17 |
| 229314 | Ventilator Mode (Hamilton) | 203,139 | 203,139 | **0** | 15 | 0 |
| 223848 | Ventilator Type | 571,964 | 376,646 | 195,318 | 6 | 2 |

**No-alternative-carrier check.** This is where the concept parts company with
`gcs`, so the table records the answer rather than assuming it.

| Carrier | Verdict |
|---|---|
| `Observation.valueString` | Written on the null-`valuenum` branch only. Recovers 19,322 / 195,318 / 0 rows — the "labels kept" column above. Already used by `attempt_0001`. |
| `Observation.valueCodeableConcept` | Not written by this ETL at all. |
| `Observation.dataAbsentReason` | Not written by this ETL at all. |
| `Observation.code` | Carries the itemid only; identical for every mode. |
| `Observation.component` | Not written by this ETL. One of the two elements the fix should use (§5). |
| `Observation.id` | UUIDv5 seeded on `ce.value` (`:20-21`). Forbidden opaque-identity inversion, refused mechanically by `sql_lint.py` (`resource-id-inversion`). Not a carrier. |
| **`Observation.valueQuantity.value` + a codebook** | **Exact.** The number still separates every mode one-to-one (§6). Reproduces all three columns with 0 NULL and 0 wrong rows, and `ventilation` identically on all 1,446,086 rows. **But the codebook is not in the IG** — see below. |

The last row is the finding, and its caveat is the reason the block survives.
The 44 codebook entries cannot be obtained from MIMIC-on-FHIR:

- `mimic-fhir/sql/codesystem/cs-chartevents-d-items.sql` selects `itemid AS code,
  label AS display` — item codes only. There is no CodeSystem for chartevents
  *values*, for these or any other itemid.
- `CodeSystem` resources are not in the served warehouse at all
  (`MIMIC_NOTES.d/ventilator_setting.md`: Pathling raised
  `IllegalArgumentException: No data found for resource type: CodeSystem`).
- It cannot be bootstrapped from the surviving `valueString`s either: the kept
  and dropped label sets are **disjoint — 0 of 63 labels appear on both
  branches** (probe, `text_branch_membership.csv`).

So the codebook can only be imported from relational MIMIC-IV — the oracle. It
is a mapping from the *source*, not from the IG, and using it would make "this
concept ports exactly" mean "ports exactly given the answer key".

## 3. Intentional or a bug?

Ruled per class, per `README.md` §3. This is the same statement `gcs.md` §3
grades, so the classes are the same and the grades are kept identical — that
consistency is the point.

| # | Class | Scope | Grade |
|---|---|---|---|
| a | `value[x]` exclusivity — `valueQuantity` and `valueString` cannot both be set | the element itself | **Inherent** |
| c | Not carrying the source text in `Observation.component`, ventilator mode/type | 1,003,717 rows across three itemids | **Bug** |
| f | No CodeSystem for chartevents *values*, so a served number has no published meaning | the same rows | **Bug**, and new to this entry |
| e | `TIMESTAMPTZ` DST normalisation at `:9,67` | 37 `only_oracle`, 29 `only_candidate`, 2 conflicts, residual 0 | **Repairable defect, already `accept`** |

**(a) is inherent and is not a hedge.** `Observation.value[x]` is a FHIR choice
type; populating both variants is non-conformant. The exclusivity is forced by
the spec.

**(c) is a bug on grounds that do not touch (a).** `Observation.component` is a
separate `0..*` element; carrying the verbatim text there is conformant and
purely additive. And the ETL already treats `ce.value` as identity-bearing —
`:20-21` seeds the resource UUID with it. Asserting a field distinguishes rows
and then declining to serve it is self-inconsistent.

**(f) is this concept's own contribution, and it is the cheaper bug.** For `gcs`
a value CodeSystem would not help — `No Response` and `No Response-ETT` share
`valuenum = 1`, so no terminology can separate them. Here it is sufficient on its
own: the numbers are already distinct and already served, and publishing what
they mean would make the port exact with no change to `Observation`. `mimic-fhir`
already generates 40-odd CodeSystems (`sql/codesystem/`), so the pattern exists.

**Trap check (`README.md` §3).** The argument convicting (c) — "a conformant,
additive element was available" — applies verbatim to `gcs`'s class (b), and
both are graded **bug**, as `gcs.md` graded them. The middle tier the README
warns about is (a), a genuine spec constraint that would otherwise be used to
excuse (c); it is graded separately for exactly that reason. Nothing here is
graded inherent on the strength of an argument that convicts something else.

**Which way this cuts.** Grading (c) and (f) repairable does **not** weaken the
block, and it does not strengthen an acceptance either — `README.md` is explicit
that "it is an upstream bug" is not by itself a reason to accept a loss. What
carries the block is §2 (the recovery is not IG-derivable) and §7 (the absence
does not stay visible). §3 only says how long that will remain true.

## 4. Example of the loss

From `attempt_0001/comparison.full.json` → `diff.samples.differing_null_only[0]`:

| column | oracle | port (`attempt_0001`) |
|---|---|---|
| `subject_id` | 10001884 | 10001884 |
| `stay_id` | 37510196 | 37510196 |
| `charttime` | 2131-01-11T11:00:00 | 2131-01-11T11:00:00 |
| `fio2` | 50.0 | 50.0 |
| `peep` | 5.199999809265137 | 5.199999809265137 |
| `plateau_pressure` | 23.0 | 23.0 |
| `respiratory_rate_set` | 20.0 | 20.0 |
| `tidal_volume_set` | 400.0 | 400.0 |
| `tidal_volume_observed` | 430.0 | 430.0 |
| `ventilator_mode_hamilton` | **APV (cmv)** | **NULL** |

Every numeric column is exact; the one text column present is absent. The served
resource that explains it: the `Observation` for itemid 229314 at that
`stay_id`/`charttime` carries `valueQuantity.value = 9` with `valueString`
absent. Relational MIMIC-IV holds `value = 'APV (cmv)'`, `valuenum = 9`.

**This is the row that distinguishes the concept from `gcs`.** The `9` is not
ambiguous — across all of MIMIC-IV, itemid 229314 `valuenum = 9` means
`APV (cmv)` and nothing else, on 93,563 rows (probe, `codebook.csv`). The
information needed to score this row is still in the served data; what is missing
is the sentence saying that 9 means `APV (cmv)`. `APV (cmv)` is in
`ventilation.sql:99`'s invasive list, so this row is `InvasiveVent` in the
oracle and unclassifiable in the port.

## 5. What a fix would look like

§3 calls (c) and (f) fixable. Either alone is sufficient here; (f) is smaller.
Both belong on kind-lab/mimic-fhir#125.

**Fix 1 — the `component` patch (fixes `gcs` and this concept together).**
Patch `fhir_observation_chartevents.sql:69-80` to keep `valueQuantity` primary
and add the verbatim source text as a component, leaving `value[x]` conformant.
The SQL is given in full at `human_override/gcs.md` §5 and is not repeated.
Re-served under it, the §4 row gains
`component[0].code.coding.code = 'sourceValue'`,
`component[0].valueString = 'APV (cmv)'`, and the port reproduces it exactly.

**Fix 2 — publish a chartevents *value* CodeSystem.** Narrower, and specific to
the categorical-numeric items this concept depends on. New file
`sql/codesystem/cs-chartevents-values.sql`, following the existing pattern:

```sql
DROP TABLE IF EXISTS fhir_trm.cs_chartevents_values;
CREATE TABLE fhir_trm.cs_chartevents_values(
    code      VARCHAR NOT NULL,
    display   VARCHAR
);

-- One row per (itemid, valuenum) that carries a distinct label. Only items
-- where the pair is unambiguous qualify; the ambiguous ones (GCS 223900 among
-- them) need Fix 1 instead, because no terminology can separate two labels
-- that share a number.
INSERT INTO fhir_trm.cs_chartevents_values
SELECT ce.itemid || '-' || ce.valuenum AS code
     , MIN(ce.value) AS display
FROM mimiciv_icu.chartevents ce
WHERE ce.valuenum IS NOT NULL AND ce.value IS NOT NULL
  AND ce.value !~ '^\s*-?[0-9]*\.?[0-9]+\s*$'
GROUP BY ce.itemid, ce.valuenum
HAVING count(DISTINCT ce.value) = 1;
```

For the three ventilator itemids that is exactly the 44 rows of the probe's
`codebook.csv`. With it served, the port reads the label from published
terminology rather than from the oracle, and §2's last row stops being a
caveat — which is the whole of what currently blocks this concept.

**Post-fix projection.** Either fix yields 1,006,127 / 1,006,127 rows exact on
all three text columns, less the class (e) DST rows ruled on their own merits.
This is not a projection in the loose sense: it is what variant C already
measures (§6), because variant C computes the same thing the fix would serve.

## 6. Numbers

**`attempt_0001` — the blocked port.** All from `comparison.full.json`.

| figure | value | fraction |
|---|---|---|
| oracle rows | 1,006,127 | — |
| candidate rows | 1,006,119 | delta −8 |
| `diff.identical` | 353,556 | 353,556 / 1,006,127 = 35.1403% |
| `diff.differing_null_only` | 652,532 | 652,532 / 1,006,127 = 64.8558% |
| `diff.differing_conflict` | 2 | class (e), fully attributed |
| `diff.columns_candidate_null.ventilator_mode` | 423,924 | 42.1341% |
| `diff.columns_candidate_null.ventilator_mode_hamilton` | 203,134 | 20.1897% |
| `diff.columns_candidate_null.ventilator_type` | 376,641 | 37.4346% |
| `diff.only_oracle` / `only_candidate` | 37 / 29 | class (e), `residual 0` both sides |
| `diff.excluded_as_unrepresentable` | `[]` | nothing declared |
| `divergence.blocking` | `[]` | **empty** |
| `divergence.tier` | `gap_shaped` | — |

Rows stating a **wrong** value: **0**. `attempt_0001` is already the shape `gcs`
needed `attempt_0006` to reach — it states no value it does not have. That is
why the remedy `gcs.md` prescribes (reopen and re-port emitting typed NULL) is
not available here: it is already done.

**Probe validation.** Two anchors, both from job 30314398, run before any
downstream number:

| check | result |
|---|---|
| probe's oracle rebuild vs shipped `mimiciv_derived.ventilator_setting` | 1,006,127 rows, key drift **0 / 0**, text mismatch **0** |
| probe's variant A vs `attempt_0001/candidate.full.parquet` | 1,006,090 joined, disagreements **0 / 0 / 0** on all three text columns |

So variant A *is* `attempt_0001`, and variant O *is* the oracle. The probe's
per-column counts run over 1,006,127 paired rows where the comparator runs over
the 1,006,090 it could key-match, so the probe reads 8 / 5 / 4 rows higher on the
three columns; all 17 sit inside the 37 unpaired class (e) rows the comparator
drops and the probe pairs.

**Invertibility — the measurement this entry turns on.**

| | `gcs` (223900) | 223849 | 229314 | 223848 |
|---|---:|---:|---:|---:|
| ambiguous `(itemid, valuenum)` pairs | **1** | **0** | **0** | **0** |
| rows on them | 644,776 | 0 | 0 | 0 |

The `gcs` figure is the control, measured by the same query in the same job. The
independent full-data sweep at
`/scratch3/nau025/debug-chartevents-value-drop/results/job-29804685/ambiguous_pairs.csv`
lists all 16 ambiguous pairs in MIMIC-IV; 223900 is on it and none of the three
ventilator itemids is.

**Per column, oracle vs variant A vs variant C** (probe; A = `attempt_0001`,
C = A plus the 44-entry codebook):

| column | oracle non-NULL | A non-NULL | A NULLed | A wrong | C non-NULL | C NULLed | C wrong |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ventilator_mode` | 443,254 | 19,322 | 423,932 | **0** | 443,254 | **0** | **0** |
| `ventilator_mode_hamilton` | 203,139 | **0** | 203,139 | **0** | 203,139 | **0** | **0** |
| `ventilator_type` | 571,963 | 195,318 | 376,645 | **0** | 571,963 | **0** | **0** |

Stays with any ventilator mode: oracle 30,612 → variant A 7,164 → variant C
30,612.

**Downstream — `ventilation`, row level** (probe; 1,446,086 keyed rows):

| oracle status | variant A status | rows |
|---|---|---:|
| InvasiveVent | **NULL** | 519,959 |
| InvasiveVent | InvasiveVent | 19,656 |
| InvasiveVent | SupplementalOxygen | 465 |
| InvasiveVent | NonInvasiveVent | 85 |
| InvasiveVent | HFNC | 18 |
| InvasiveVent | None | 2 |
| NonInvasiveVent | **NULL** | 1,670 |
| NonInvasiveVent | SupplementalOxygen | 9 |
| NonInvasiveVent | HFNC | 1 |

Variant C: **0** status changes of 1,446,086.

**Downstream — `ventilation`, episodes:**

| status | episodes O → A → C | stays O → A → C | hours O → A → C |
|---|---|---|---|
| InvasiveVent | 34,743 → **1,786** → 34,743 | 26,856 → **1,450** → 26,856 | 1,800,204.0 → **35,955.0** → 1,800,204.0 |
| NonInvasiveVent | 3,846 → 3,474 → 3,846 | 2,384 → 2,179 → 2,384 | 37,485.0 → 33,285.5 → 37,485.0 |
| SupplementalOxygen | 65,004 → 64,293 → 65,004 | 47,136 → **47,189** → 47,136 | 1,531,626.9 → 1,528,083.9 → 1,531,626.9 |
| Tracheostomy | 4,869 → 4,690 → 4,869 | 2,110 → 2,120 → 2,110 | 131,491.4 → 131,460.1 → 131,491.4 |

**94.9% of invasive-ventilation episodes and 98.0% of its hours disappear**, and
25,406 of 26,856 stays lose `InvasiveVent` entirely (variant C: 0). Note that
`SupplementalOxygen` and `Tracheostomy` gain *stays* while losing episodes — the
580 misclassified rows above manufacture episodes on stays that should not have
them.

**Downstream — the SOFA respiration join** (probe; `sofa.sql:40-64`):

| figure | value |
|---|---:|
| arterial blood gases | 784,486 |
| inside an `InvasiveVent` window, oracle | 202,889 |
| inside an `InvasiveVent` window, variant A | **4,758** |
| flipped ventilated → unventilated | **198,131** |
| flipped unventilated → ventilated | 0 |
| …of the flipped, carrying a non-NULL `pao2fio2ratio` | **190,111** |
| distinct ICU stays affected | **22,291** |
| flipped under variant C | **0** |

## 7. Misc

- **Why the absence does not stay visible, which is the load-bearing half.**
  `ventilator_setting` itself is clean — typed NULL, `differing_conflict = 0`
  net of DST, nothing concealed. But the NULL is consumed twice and survives
  neither. `ventilation.sql:171-180` (`vd0`) filters
  `WHERE ventilation_status IS NOT NULL`, so 519,959 unclassifiable rows are
  **deleted rather than surfaced**; then `sofa.sql:58-62` LEFT JOINs
  `ventilation`, where a missing episode is indistinguishable from "not
  ventilated". At `sofa.sql:242-247` a ventilated ratio `< 100` scores
  respiration **4**, but rescored as unventilated the first reachable arm is
  `pao2fio2ratio_novent < 300 → 2`. The result is a SOFA respiration component
  silently **2 points low** on 190,111 gases across 22,291 stays — an ordinary
  number, not an absence. This is the failure `LOOP_CONTRACT.md:481` names, one
  and two levels below the table that is honest.
- **Essential-loss test (`LOOP_CONTRACT.md:481`), term by term, on
  `attempt_0001`.** *Row inclusion:* unchanged in this table — 1,006,127 in,
  1,006,119 out, the 37/29 split fully attributed to class (e) with
  `residual 0`. *Semantic grain:* unchanged — `(subject_id, charttime)` still
  identifies one row. *Grouping:* unaffected, upstream of the NULL. *Temporal
  carry-forward:* **reached** — `ventilation.sql`'s `LAG`/`LEAD` episode
  assembly runs over rows the NULL removed, so 94.9% of invasive episodes never
  form. *Contamination of representable values:* **reached, and not only
  downstream** — 580 `ventilation` rows take a wrong non-NULL status, and 190,111
  SOFA gas measurements take a wrong score. Two of five terms are touched and
  the fifth is touched in the worst available way. `gcs`'s accepted position
  touched the fifth term only at the dependent level and only if a stated
  condition went unhonoured; this touches it unconditionally.
- **Why `gcs`'s acceptance does not transfer.** `gcs.md` §7 recorded that
  `ventilator_setting` "should be reopened under the same reasoning or the two
  verdicts contradict each other", citing `LOOP_CONTRACT.md:512-516`. That
  condition is discharged here, and the answer is no. `:512-516` says to rule on
  the concept rather than on which column the builder reached first — it does
  not say two concepts sharing an ETL statement share a verdict. The evidence
  differs on the one axis that decided `gcs`: its best alternative carriers
  measured 4.7% recall (`oxygen_delivery`) and 80.1% accuracy (oracle
  `ventilation`), which is what earned "every defensible mapping was tried". The
  equivalent measurement here is **100.00%**, exact on every row and every
  column. A concept cannot be accepted on the ground that nothing recovers the
  value when something does.
- **What would change this ruling.** Exactly one thing: a decision that the
  44-entry codebook is an admissible mapping. It is exact, so
  `LOOP_CONTRACT.md:406-411` does not bar it — that rule bars *approximations*,
  and "an approximation is only admissible if it is exact" is satisfied. It is
  not opaque-identity inversion: no hash, no id parsing, and `sql_lint.py` would
  not refuse a plain `CASE` (its two rules fire on `UNHEX` of a 32-hex namespace
  and on hash calls). The objection is narrower and is §2's: the literals are
  not in the IG, cannot be derived from served data, and can only come from the
  oracle — so the port would be reading the answer key, and its exactness would
  itself be an oracle-derived claim. That is a judgement about what "mapping"
  means, and it is a human's to make. If it is made the other way, the correct
  move is `retry` to `attempt_0002` with the codebook, **not** an override of
  `attempt_0001`.
- **Declaration mechanics, if this is ever accepted instead.**
  `ventilator_mode_hamilton` is 100% NULL and belongs in `unrepresentable.json`.
  `ventilator_mode` (95.6% NULL) and `ventilator_type` (65.8%) must **not** be
  declared — a partial declaration is a blocking
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:439-443`). Any such
  acceptance must also carry a condition on `sofa`: its `pafi` CTE must emit
  NULL for a gas whose ventilation status is unknown rather than routing it to
  `pao2fio2ratio_novent`. Unhonoured, that is the 190,111 silently-low scores
  above. This is the analogue of `gcs.md`'s condition 1 and it bites far harder
  — 22,291 stays against 4,645.
- **`ventilator_type` is collateral, not damage.** 376,645 NULLed rows and
  **zero** consumers: `ventilation.sql` is the only reader of
  `ventilator_setting` in the 65-concept DAG, and it selects only
  `ventilator_mode` and `ventilator_mode_hamilton`. The whole of the downstream
  argument rests on the two mode columns.
- **Cost of the block, stated plainly.** This gates 7 of 65 concepts:
  `ventilation` directly, and through it `sofa`, `sapsii`, `oasis`, `lods`,
  `apsiii` and `first_day_sofa` (`concept_dag.json`). That is a real price and
  it is not an argument against the ruling; it is the reason to push §5 upstream
  rather than wait.
- **Consistency with earlier verdicts.** `antibiotic` and `nsaid` accepted gaps
  that changed no computed value and contaminated nothing. `gcs` accepted one
  that reached temporal carry-forward but stayed a typed NULL at every level a
  condition could hold. This one reaches carry-forward *and* contaminates
  representable values in two dependents with no condition that can be honoured
  without gutting `sofa`. It is the first of the four where the loss gets
  materially worse the further from the table you look, which is the ordering
  `LOOP_CONTRACT.md:905-911` cares about.
- **Class (e) is not this entry's subject.** The 37 `only_oracle`, 29
  `only_candidate` and 2 conflicts are fully attributed to the upstream
  `TIMESTAMPTZ` cast with `residual_rows: 0` and `complete: True` on both
  attributions, at 37/1,006,127. Per `LOOP_CONTRACT.md:256-315` a proven DST
  shift is `accept` and never `blocked`; it neither supports nor weakens
  anything above.
- **Caveats.** (i) Every variant-A/C figure in §6 is a probe simulation, not a
  port artifact; §6's two anchors are what license reading them as statements
  about `attempt_0001`, and variant C in particular has never been run through
  Pathling against the served warehouse — it is a relational upper bound. (ii)
  The probe rebuilds `ventilation` from `ventilation.sql` rather than comparing
  against a shipped `mimiciv_derived.ventilation`, which is absent from the
  oracle; all three variants pass through the same transcription, so the O-vs-A
  contrast is sound while absolute episode counts carry that transcription's
  error bar. (iii) The judge is not re-called on `attempt_0001`; nothing here
  asks it to be.
- **`state.json` — recommended, NOT yet applied.** Nothing in
  `state/ventilator_setting/state.json` was changed by this review. Its
  `error_message` still carries the judge's original ground ("the missing
  ventilator mode/type text is essential"), which §1 replaces, so the state file
  and this entry currently disagree about *why* the concept is blocked. The
  recommended repair is to rewrite `error_message` to the corrected ground — the
  discriminator is served but unlabelled, no served terminology labels it, and
  the block rests on §2 and §7 — leaving `status`, `attempt`,
  `divergence_decided_by` and every counter untouched. It is left unapplied
  because `state.json` is written by `mimic_utils` and no subcommand edits that
  field alone; a hand-edit would race the ledger under
  `.opencode/goals/`. Until it is done, this file is the authority on the
  reason and the state file on the verdict. The concept remains
  `BLOCKED_REPRESENTATION` either way, and is **not** reported on any of the
  four `status` lines for exact match, judge acceptance, human override, or
  reopen.
- **Revisions.** None. First version, 2026-08-21.
