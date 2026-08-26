# `antibiotic` — human override out of `BLOCKED_REPRESENTATION`

- **Applied:** 2026-08-25 (re-applied; supersedes the 2026-08-21 override of
  `attempt_0003`, which measured the same loss against the pre-rebuild warehouse)
- **Transition:** `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, `--by human`
- **Attempt:** `concepts/medication/antibiotic/attempt_0004`
- **Canonical SQL:** `mimic-iv/concepts/medication/antibiotic.sql`
- **Fidelity:** 692,009 / 735,462 identical (94.0917%), row counts equal

## 0. Why this document was re-applied

`attempt_0004` is a `[replay:data_rebuild]` of `attempt_0003` against the
MIMIC-on-FHIR warehouse rebuilt on 2026-08-24. `concept.sql` and all six
ViewDefinitions were carried forward byte-identical (`sha256` recorded in
`attempt_0004/replay_provenance.json`; `concept.sql` hashes match at
`23533b07…`), so the only variable that changed was the served data.

One of the two fixes in that rebuild reached this concept, and it closed the
DST divergence completely:

| | `attempt_0003` | `attempt_0004` |
|---|---|---|
| `differing_conflict` | 70 | **0** |
| `diff.conflict_attribution` | `upstream_timestamptz_dst_shift` | `null` |
| `divergence.tier` | `contested` | **`gap_shaped`** |
| identical | 691,939 (94.0822%) | 692,009 (94.0917%) |

The +70 identical rows are exactly the 70 former DST conflicts, and
`columns_conflicting` went from `{starttime: 52, stoptime: 23}` to `{}`. The
reopen reason directed that a surviving hour-wide shift be treated as a finding
rather than an artifact; none survives, so that condition is not triggered.

Everything else is unchanged to the row: `differing_null_only` 43,453,
`columns_candidate_null` `{starttime: 43369, stoptime: 43422, stay_id: 13494}`,
`only_oracle`/`only_candidate` 0/0. The residual is the identical gap this
document was written about, now measured on the lower `gap_shaped` bar.

## 1. The problem

43,453 of 735,462 antibiotic prescriptions (5.91%) come back from MIMIC-on-FHIR
with no `starttime` and no `stoptime`, and 13,494 of those consequently have no
`stay_id`. All rows are present and all other columns are exact; the loss is
confined to timing.

The equivalence judge ruled that loss *essential* and blocked the concept
again on the rebuilt data (`attempt_0004/evidence/equivalence-judge.md`): "The
43,453 null-only residual rows are intrinsic but essential: missing `starttime`
removes 13,494 ICU assignments and destroys temporal event grain used by
downstream infection-window logic." That is the same finding the `attempt_0003`
judge made and this document rejected; per `LOOP_CONTRACT.md:850-856` the judge
is not called to reconsider its own ruling and has no channel through which a
prior override binds it, so the re-block carries no new evidence.

The unrecoverability is correct (§2). The *essential* finding is what this
override rejects: the absence changes no row's inclusion, no grain, no grouping,
no carry-forward and no computed value — it is emitted as typed NULL, never as an
estimate — so `LOOP_CONTRACT.md:481` is not met (§7).

## 2. What caused it

`mimic-fhir/sql/fhir_medication_request.sql:172-177`:

```sql
, 'dispenseRequest', CASE WHEN ph_STARTTIME IS NOT NULL AND (ph_STARTTIME <= ph_STOPTIME) THEN jsonb_build_object(
       'validityPeriod', jsonb_build_object(
             'start', ph_STARTTIME
             , 'end', ph_STOPTIME
        )
  ) ELSE NULL END
```

`MedicationRequest.dispenseRequest.validityPeriod` is the **only** served carrier
of `prescriptions.starttime`/`stoptime`. The guard is all-or-nothing: when it
fails, the entire `dispenseRequest` is omitted — both endpoints, not one. It
fails on two source shapes, a **reversed** interval (`start > stop`) and an
**incomplete** one (either endpoint NULL — note `NULL <= x` is SQL NULL, not
`true`, so a present endpoint is discarded along with the missing one).

Nothing else in the IG carries these values:

- `authoredOn` (`:55,124`) is pharmacy `entertime`, a third timestamp.
- `fhir_medication_dispense.sql` carries no prescription times (its only `Period`
  is `maxDosePerPeriod` at `:142`).
- `fhir_medication_administration.sql:177` carries emar `charttime` —
  administration events, a different table and grain.
- Identifiers (`:75,111-124`) carry identity only; recovering a value by
  inverting a resource id is refused by `LOOP_CONTRACT.md:317-333` and by
  `src/mimic_utils/sql_lint.py`.

`stay_id` follows from `starttime`: `antibiotic.sql:198-201` LEFT JOINs
`icustays` on `pr.starttime >= ie.intime AND pr.starttime < ie.outtime`.

## 3. Intentional or a bug?

Three tiers, because one guard produces losses of three different kinds:

| tier | what is lost | verdict |
|---|---|---|
| 1 | both endpoints of an **incomplete** interval, where one was present and sound | **bug** — NULL-unsafe comparison, nothing to weigh |
| 2 | the **first** endpoint of a **reversed** pair | **fixable, but arguable** — the spec permits emitting it; upstream declining to is a judgement |
| 3 | the **second** endpoint of a **reversed** pair | **inherent** — `per-1` forbids it sharing the `Period` |
| — | 70 rows shifted one hour by the `TIMESTAMPTZ` cast at `:43-44` | **fixed upstream** — `mimic-fhir ade10fb` (#124); 0 rows in `attempt_0004` |

The fourth row was a real bug, carried under the `LOOP_CONTRACT.md:256-315`
exemption in the 2026-08-21 override. It is no longer exempted because it no
longer occurs: the ETL now generates under UTC, which has no spring-forward gap
in any year, so the cast is an identity on the wall clock. Tiers 1–3 are
untouched by that fix and are the whole of the remaining loss.

FHIR R4 `Period` carries invariant `per-1`: *"If present, start SHALL have a
lower or equal value than end."* That forbids the two endpoints of a reversed
pair **sharing one `Period`** — it forbids neither value on its own, since
`Period.start` and `Period.end` are each `0..1`. So on a reversed row exactly one
endpoint was always emittable (tier 2) and exactly one is genuinely excluded
(tier 3). Which is which is upstream's choice of what to keep.

Tier 2 is arguable rather than plainly wrong: with `start > stop` you know one of
the two values is corrupt and not which, so emitting the recorded start as an
open-ended period asserts a reliability the source does not support. Tier 1 has
no such defence — there the other value is simply absent.

## 4. Example of the loss

A real affected row, from `attempt_0004/comparison.full.json`
(`diff.samples.substitutions`) — reversed interval, and one of the 13,494 that
also loses an ICU stay:

| | `subject_id` | `hadm_id` | `antibiotic` | `route` | `starttime` | `stoptime` | `stay_id` |
|---|---|---|---|---|---|---|---|
| **relational MIMIC-IV (oracle)** | 17975714 | 24260580 | Vancomycin | IV | `2167-02-11 08:00` | `2167-02-11 04:00` | 35808699 |
| **port over MIMIC-on-FHIR** | 17975714 | 24260580 | Vancomycin | IV | `NULL` | `NULL` | `NULL` |

The prescription's recorded stop precedes its start by four hours, so the guard
fails and the served `MedicationRequest` has no `dispenseRequest` at all:

```json
{ "resourceType": "MedicationRequest", "status": "...", "authoredOn": "…entertime…" }
```

With `validityPeriod.start` absent there is nothing to compare against
`icustays.intime`/`outtime`, so `stay_id` 35808699 is lost as well — one source
absence, three NULL columns.

## 5. What a fix would look like

Tiers 1 and 2 are recoverable upstream by making the guard emit whichever bounds
are individually valid instead of requiring a complete valid pair:

```sql
, 'dispenseRequest', CASE WHEN ph_STARTTIME IS NOT NULL OR ph_STOPTIME IS NOT NULL THEN jsonb_build_object(
       'validityPeriod', CASE
           -- complete and ordered: unchanged from today
           WHEN ph_STARTTIME IS NOT NULL AND ph_STOPTIME IS NOT NULL
                AND ph_STARTTIME <= ph_STOPTIME
                THEN jsonb_build_object('start', ph_STARTTIME, 'end', ph_STOPTIME)
           -- reversed or incomplete: emit the bound `per-1` permits, drop the other
           WHEN ph_STARTTIME IS NOT NULL THEN jsonb_build_object('start', ph_STARTTIME)
           ELSE jsonb_build_object('end', ph_STOPTIME)
       END
  ) ELSE NULL END
```

The §4 row would then serve as:

```json
{ "resourceType": "MedicationRequest",
  "dispenseRequest": { "validityPeriod": { "start": "2167-02-11T08:00:00+00:00" } } }
```

(`+00:00` rather than the `-04:00` this document showed before 2026-08-24: the
ETL now generates under UTC, so the served offset no longer moves with the
season and the wall clock survives the round trip.)

and the port — unchanged, no edit to `concept.sql` — would produce:

| | `starttime` | `stoptime` | `stay_id` |
|---|---|---|---|
| oracle | `2167-02-11 08:00` | `2167-02-11 04:00` | 35808699 |
| port, post-fix | `2167-02-11 08:00` | `NULL` | **35808699** |

`starttime` and `stay_id` return; `stoptime` stays NULL, and that residual is
tier 3 — it needs a `MedicationRequest` extension, i.e. an IG design change, not
a defect repair.

## 6. Numbers

From `attempt_0004/comparison.full.json`, with `attempt_0003` alongside so the
effect of the rebuild is legible:

| | `attempt_0003` | `attempt_0004` | of 735,462 |
|---|---|---|---|
| identical | 691,939 | **692,009** | 94.0917% |
| `differing_null_only` (this gap) | 43,453 | 43,453 | 5.9083% |
| `differing_conflict` (DST cast) | 70 | **0** | — |
| `only_oracle` / `only_candidate` after pairing | 0 / 0 | 0 / 0 | — |

Candidate NULL where the oracle holds a value, unchanged by the rebuild:
`stoptime` 43,422 (5.902%), `starttime` 43,369 (5.897%), `stay_id` 13,494
(1.835%). Conflicts: none — `columns_conflicting` is `{}`.

Those column counts reconstruct the source shape exactly — oracle `starttime`
itself NULL on 43,453 − 43,369 = **84** rows, oracle `stoptime` itself NULL on
43,453 − 43,422 = **31**, both present but reversed on the remaining **43,338** —
matching `MIMIC_NOTES.md:472` ("43,338 reversed and 115 one-sided-NULL")
derived independently.

By tier:

| tier | scope | affected |
|---|---|---|
| 1 — bug | incomplete intervals | **115 rows** (0.0156%) |
| 2 — fixable, arguable | first endpoint of each reversed pair | **43,338 values** |
| 3 — inherent | second endpoint of each reversed pair | **43,338 values** |
| DST — bug, fixed upstream | one-hour shift | **0 rows** (was 70) |

**Post-fix projection.** With §5 applied upstream, tiers 1 and 2 close: zero
`starttime` NULLs, zero `stay_id` NULLs, residual `stoptime` NULL on 43,338 rows,
fidelity 692,124 / 735,462 = 94.1074%. A small move in the headline number and a
complete change in character — no timing input to any derivation would be
missing. (The 2026-08-21 projection of 692,054 was the same arithmetic less the
70 DST rows, which have since been recovered by the rebuild.)

## 7. Misc

- **Why the loss is acceptable** (`LOOP_CONTRACT.md:481`, term by term): row
  inclusion unchanged (735,462 = 735,462, `delta: 0`; inclusion is a
  name-and-route filter with no temporal predicate); grain unchanged (paired 1:1
  on `(subject_id, hadm_id, antibiotic, route)` with matching multiplicity, zero
  `only_oracle`/`only_candidate`); no `GROUP BY`, window or carry-forward in the
  concept; no fan-out lost (the `icustays` join is against non-overlapping stays
  within one `hadm_id`, so it matches at most once); no contamination, since the
  gap is typed NULL rather than the estimate `LOOP_CONTRACT.md:406-411` warns
  about.
- **The same evidence has now been accepted three times.** `attempt_0002`,
  `attempt_0003` and `attempt_0004` have the same `differing_null_only` residual
  to the row; `diff` on the 0002/0003 `concept.sql` is four additive key
  projections and a reworded comment, and 0003→0004 is byte-identical (§0).
  Attempts 0001 and 0002 were judge-accepted on this gap; 0003 was
  human-accepted.
- **Siblings with the same ETL were re-accepted by the judge in this very
  rebuild wave.** `acei`, `arb` and `nsaid` were all replayed against the same
  2026-08-24 warehouse and all three returned `COMPLETED_WITH_DIVERGENCE` with
  `divergence_decided_by: judge`, each citing
  `fhir_medication_request.sql:172-177` and the absent
  `dispenseRequest.validityPeriod` — `acei` at 9,059 null-only rows of 112,014
  (8.09%), `arb` at 3,179 of 39,534 (8.04%), both *larger* affected fractions
  than antibiotic's 5.91%. So on one ETL defect, in one wave, the judge accepted
  the siblings and blocked this concept. `LOOP_CONTRACT.md:512-516` rules against
  splitting identical concepts this way — *"Rule on the concept, never on which
  column the builder reached first."*
- **The one real asymmetry against those siblings holds up.** `acei` and `arb`
  project the endpoints but derive nothing from them; antibiotic additionally
  derives `stay_id`, which is what the judge leans on. It survives the
  `LOOP_CONTRACT.md:481` test anyway because the ICU join is a `LEFT JOIN` on
  both sides — `mimic-iv/concepts/medication/antibiotic.sql:198-201` and
  `attempt_0004/concept.sql:265-268` — so a NULL `starttime` drops the ICU match
  without dropping the row. `row_count.delta: 0` confirms it on the data rather
  than by reading the SQL.
- **Downstream.** `suspicion_of_infection.sql:8-10,84-93` reads
  `antibiotic.starttime` into ±24h/±72h culture windows, so `sepsis3` onset is
  affected. Per `LOOP_CONTRACT.md:929-950` those concepts inherit and cite this
  acceptance rather than re-deriving it. Note also that this concern lives
  entirely in tier 2 — the fixable side (§5). `suspicion_of_infection` currently
  holds a verdict earned 2026-08-21, i.e. against the pre-rebuild warehouse, and
  still needs its own replay; it was blocked from running while this concept sat
  reopened.
- **Not a declaration.** `unrepresentable.json` is the wrong instrument: the
  columns are not 100% NULL, so the comparator would reject it as
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:420-423,440-446`).
- **Caveat.** A NULL `stay_id` is indistinguishable from "not during an ICU
  stay", so a naive consumer under-counts silently rather than erroring. Stated,
  not fixed — the column is present and NULL, so dependents execute and
  re-classify the inherited NULLs visibly (`LOOP_CONTRACT.md:905-911`).
- **Spec check.** `per-1` and the `0..1` cardinalities are base FHIR R4. The
  `mimic-profiles` submodule is not checked out in this working copy, so no
  profile-level tightening of `validityPeriod` was verified.
- **Tier 1 is still an open upstream defect.** The 115 one-sided-NULL rows lost
  to the NULL-unsafe guard have no defence (§3) and are *not* on the
  "still open, deliberately" list in `TODO_upstream_fix_rerun.md`. Small, but it
  is the part of this loss that should be filed upstream rather than carried
  forward indefinitely.
- **Revision.** §3 was revised on 2026-08-21, the day of the first override, in
  review. It first split the loss two ways — reversed "inherent", incomplete "a
  bug" — which contradicted itself, since the conformance argument convicting the
  second also applies to half of the first. The three-tier ruling replaces it and
  moves loss out of the inherent column. On 2026-08-25 the document was
  re-measured against `attempt_0004` (§0): the DST row of §3 moved from
  "exempted" to "fixed upstream", and the §4/§5 worked example was replaced with
  one drawn from `attempt_0004`'s own samples so every figure here is citable
  from the attempt it heads.
