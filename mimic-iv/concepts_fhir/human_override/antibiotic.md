# `antibiotic` — human override out of `BLOCKED_REPRESENTATION`

- **Applied:** 2026-08-21
- **Transition:** `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, `--by human`
- **Attempt:** `concepts/medication/antibiotic/attempt_0003`
- **Canonical SQL:** `mimic-iv/concepts/medication/antibiotic.sql`
- **Fidelity:** 691,939 / 735,462 identical (94.0822%), row counts equal

## 1. The problem

43,453 of 735,462 antibiotic prescriptions (5.91%) come back from MIMIC-on-FHIR
with no `starttime` and no `stoptime`, and 13,494 of those consequently have no
`stay_id`. All rows are present and all other columns are exact; the loss is
confined to timing.

The equivalence judge ruled that loss *essential* and blocked the concept
(`attempt_0003/evidence/equivalence-judge.md`): "Missing starttime removes core
timing and the canonical half-open ICU assignment […] no FHIR query can recover
it. This is not ancillary loss, so the result is not a faithful port."

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
| — | 70 rows shifted one hour by the `TIMESTAMPTZ` cast at `:43-44` | **bug**, already exempted by `LOOP_CONTRACT.md:256-315` |

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

A real affected row, from `attempt_0003/comparison.full.json`
(`diff.samples.substitutions`) — reversed interval, and one of the 13,494 that
also loses an ICU stay:

| | `subject_id` | `hadm_id` | `antibiotic` | `route` | `starttime` | `stoptime` | `stay_id` |
|---|---|---|---|---|---|---|---|
| **relational MIMIC-IV (oracle)** | 17541182 | 29181905 | Vancomycin | IV | `2177-10-09 20:00` | `2177-10-09 16:00` | 37584134 |
| **port over MIMIC-on-FHIR** | 17541182 | 29181905 | Vancomycin | IV | `NULL` | `NULL` | `NULL` |

The prescription's recorded stop precedes its start by four hours, so the guard
fails and the served `MedicationRequest` has no `dispenseRequest` at all:

```json
{ "resourceType": "MedicationRequest", "status": "...", "authoredOn": "…entertime…" }
```

With `validityPeriod.start` absent there is nothing to compare against
`icustays.intime`/`outtime`, so `stay_id` 37584134 is lost as well — one source
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
  "dispenseRequest": { "validityPeriod": { "start": "2177-10-09T20:00:00-04:00" } } }
```

and the port — unchanged, no edit to `concept.sql` — would produce:

| | `starttime` | `stoptime` | `stay_id` |
|---|---|---|---|
| oracle | `2177-10-09 20:00` | `2177-10-09 16:00` | 37584134 |
| port, post-fix | `2177-10-09 20:00` | `NULL` | **37584134** |

`starttime` and `stay_id` return; `stoptime` stays NULL, and that residual is
tier 3 — it needs a `MedicationRequest` extension, i.e. an IG design change, not
a defect repair.

## 6. Numbers

From `attempt_0003/comparison.full.json`:

| | rows | of 735,462 |
|---|---|---|
| identical | 691,939 | 94.0822% |
| `differing_null_only` (this gap) | 43,453 | 5.9083% |
| `differing_conflict` (DST cast) | 70 | 0.0095% |
| `only_oracle` / `only_candidate` after pairing | 0 / 0 | — |

Candidate NULL where the oracle holds a value: `stoptime` 43,422 (5.902%),
`starttime` 43,369 (5.897%), `stay_id` 13,494 (1.835%). Conflicts: `starttime`
52, `stoptime` 23.

Those column counts reconstruct the source shape exactly — oracle `starttime`
itself NULL on 43,453 − 43,369 = **84** rows, oracle `stoptime` itself NULL on
43,453 − 43,422 = **31**, both present but reversed on the remaining **43,338** —
matching `MIMIC_NOTES.md:412-415` ("43,338 reversed and 115 one-sided-NULL")
derived independently.

By tier:

| tier | scope | affected |
|---|---|---|
| 1 — bug | incomplete intervals | **115 rows** (0.0156%) |
| 2 — fixable, arguable | first endpoint of each reversed pair | **43,338 values** |
| 3 — inherent | second endpoint of each reversed pair | **43,338 values** |
| DST — bug, exempted | one-hour shift | **70 rows** (0.0095%) |

**Post-fix projection.** With §5 applied upstream, tiers 1 and 2 close: zero
`starttime` NULLs, zero `stay_id` NULLs, residual `stoptime` NULL on 43,338 rows,
fidelity 692,054 / 735,462 = 94.098%. A small move in the headline number and a
complete change in character — no timing input to any derivation would be
missing.

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
- **The same evidence was accepted twice before.** `attempt_0002` and
  `attempt_0003` have numerically identical comparisons; `diff` on their
  `concept.sql` is four additive key projections and a reworded comment, matching
  the shape-only reopen reason in `state.json`. Attempts 0001 and 0002 were both
  judge-accepted on this gap.
- **Siblings with the same ETL and larger fractions were accepted:** `acei`
  (8.09%) and `arb` (8.04%). `LOOP_CONTRACT.md:512-516` rules against splitting
  identical concepts this way — *"Rule on the concept, never on which column the
  builder reached first."*
- **Downstream.** `suspicion_of_infection.sql:8-10,84-93` reads
  `antibiotic.starttime` into ±24h/±72h culture windows, so `sepsis3` onset is
  affected. Per `LOOP_CONTRACT.md:929-950` those concepts inherit and cite this
  acceptance rather than re-deriving it. Note also that this concern lives
  entirely in tier 2 — the fixable side (§5).
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
- **Revision.** §3 was revised on 2026-08-21, the day of the override, in
  review. It first split the loss two ways — reversed "inherent", incomplete "a
  bug" — which contradicted itself, since the conformance argument convicting the
  second also applies to half of the first. The three-tier ruling replaces it and
  moves loss out of the inherent column.
