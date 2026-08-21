# `nsaid` — human override out of `BLOCKED_REPRESENTATION`

- **Applied:** 2026-08-21
- **Transition:** `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, `--by human`
- **Attempt:** `concepts/medication/nsaid/attempt_0002`
- **Canonical SQL:** `mimic-iv/concepts/medication/nsaid.sql`
- **Fidelity:** 225,384 / 235,678 identical (95.6322%), row counts equal

Same cause and same ruling as `human_override/antibiotic.md`, which carries the
fuller treatment of the shared ETL statement. This file states the `nsaid`
specifics.

## 1. The problem

10,276 of 235,678 NSAID prescriptions (4.36%) come back from MIMIC-on-FHIR with
no `starttime` and no `stoptime`. All rows are present and every other column is
exact. `nsaid.sql` projects only `subject_id, hadm_id, nsaid, starttime,
stoptime`, so there is no derived column and no `stay_id` for the gap to reach.

The equivalence judge blocked the concept
(`attempt_0002/evidence/equivalence-judge.md`): "Because canonical
`nsaid.sql:30-35` emits the prescription start and stop times, the missing
clinically meaningful timing is essential."

That reduces to "the concept projects a timestamp column, therefore any gap in it
is essential" — a test no time-carrying concept can pass, and one
`LOOP_CONTRACT.md:413-418` rejects outright: *"Test what the absence reaches, not
whether it sounds clinically important."* Here it reaches nothing (§7).

## 2. What caused it

`mimic-fhir/sql/fhir_medication_request.sql:172-177` — the all-or-nothing guard:

```sql
, 'dispenseRequest', CASE WHEN ph_STARTTIME IS NOT NULL AND (ph_STARTTIME <= ph_STOPTIME) THEN jsonb_build_object(
       'validityPeriod', jsonb_build_object(
             'start', ph_STARTTIME
             , 'end', ph_STOPTIME
        )
  ) ELSE NULL END
```

`MedicationRequest.dispenseRequest.validityPeriod` is the only served carrier of
`prescriptions.starttime`/`stoptime`. When the guard fails the whole
`dispenseRequest` is omitted — both endpoints together. It fails on a **reversed**
interval (`start > stop`) and on an **incomplete** one (`NULL <= x` is SQL NULL,
not `true`, so a present endpoint goes with the missing one).

No alternative carrier: `authoredOn` (`:55,124`) is pharmacy `entertime`;
`fhir_medication_dispense.sql` carries no prescription times (only
`maxDosePerPeriod` at `:142`); `fhir_medication_administration.sql:177` carries
emar `charttime` at another grain; identifiers carry identity only, and resource-id
inversion is refused by `LOOP_CONTRACT.md:317-333` and `src/mimic_utils/sql_lint.py`.

## 3. Intentional or a bug?

| tier | what is lost | verdict |
|---|---|---|
| 1 | both endpoints of an **incomplete** interval, where `starttime` was present and sound | **bug** — NULL-unsafe comparison, nothing to weigh |
| 2 | the **first** endpoint of a **reversed** pair | **fixable, but arguable** — the spec permits emitting it |
| 3 | the **second** endpoint of a **reversed** pair | **inherent** — `per-1` forbids it sharing the `Period` |
| — | 18 rows shifted one hour by the `TIMESTAMPTZ` cast at `:43-44` | **bug**, already exempted by `LOOP_CONTRACT.md:256-315` |

FHIR R4 `Period` carries invariant `per-1`: *"If present, start SHALL have a
lower or equal value than end."* It forbids the two endpoints of a reversed pair
**sharing one `Period`**, not either value on its own — `Period.start` and
`Period.end` are each `0..1`. So on a reversed row one endpoint was always
emittable (tier 2) and one is genuinely excluded (tier 3); which is which is
upstream's choice.

Tier 2 is arguable rather than plainly wrong: with `start > stop` one of the two
values is corrupt and you cannot tell which, so emitting the recorded start as an
open-ended period asserts a reliability the source does not support. Tier 1 has
no such defence.

## 4. Example of the loss

A real affected row, from `attempt_0002/comparison.full.json`
(`diff.samples.substitutions`):

| | `subject_id` | `hadm_id` | `nsaid` | `starttime` | `stoptime` |
|---|---|---|---|---|---|
| **relational MIMIC-IV (oracle)** | 10011398 | 27505812 | Aspirin | `2146-12-16 10:00` | `2146-12-15 17:00` |
| **port over MIMIC-on-FHIR** | 10011398 | 27505812 | Aspirin | `NULL` | `NULL` |

The recorded stop precedes the start by 17 hours, so the guard fails and the
served resource has no `dispenseRequest` at all:

```json
{ "resourceType": "MedicationRequest", "status": "...", "authoredOn": "…entertime…" }
```

## 5. What a fix would look like

Identical to `antibiotic.md:§5` — make the guard emit whichever bounds are
individually valid rather than requiring a complete valid pair:

```sql
, 'dispenseRequest', CASE WHEN ph_STARTTIME IS NOT NULL OR ph_STOPTIME IS NOT NULL THEN jsonb_build_object(
       'validityPeriod', CASE
           WHEN ph_STARTTIME IS NOT NULL AND ph_STOPTIME IS NOT NULL
                AND ph_STARTTIME <= ph_STOPTIME
                THEN jsonb_build_object('start', ph_STARTTIME, 'end', ph_STOPTIME)
           WHEN ph_STARTTIME IS NOT NULL THEN jsonb_build_object('start', ph_STARTTIME)
           ELSE jsonb_build_object('end', ph_STOPTIME)
       END
  ) ELSE NULL END
```

The §4 row would then serve as:

```json
{ "resourceType": "MedicationRequest",
  "dispenseRequest": { "validityPeriod": { "start": "2146-12-16T10:00:00-05:00" } } }
```

and the port — unchanged, no edit to `concept.sql` — would produce:

| | `starttime` | `stoptime` |
|---|---|---|
| oracle | `2146-12-16 10:00` | `2146-12-15 17:00` |
| port, post-fix | `2146-12-16 10:00` | `NULL` |

`starttime` returns; `stoptime` stays NULL as tier 3, which would need a
`MedicationRequest` extension — an IG design change, not a defect repair.

## 6. Numbers

From `attempt_0002/comparison.full.json`:

| | rows | of 235,678 |
|---|---|---|
| identical | 225,384 | 95.6322% |
| `differing_null_only` (this gap) | 10,276 | 4.3603% |
| `differing_conflict` (DST cast, fully attributed) | 18 | 0.0076% |
| `only_oracle` / `only_candidate` after pairing | 0 / 0 | — |

Candidate NULL where the oracle holds a value: `starttime` 10,276 (4.360%),
`stoptime` 10,249 (4.349%). Conflicts: `starttime` 12, `stoptime` 6.

Source shape reconstructed from those counts: oracle `starttime` itself NULL on
10,276 − 10,276 = **0** rows, oracle `stoptime` itself NULL on 10,276 − 10,249 =
**27**, both present but reversed on the remaining **10,249**.

By tier:

| tier | scope | affected |
|---|---|---|
| 1 — bug | incomplete intervals | **27 rows** (0.0115%) |
| 2 — fixable, arguable | first endpoint of each reversed pair | **10,249 values** |
| 3 — inherent | second endpoint of each reversed pair | **10,249 values** |
| DST — bug, exempted | one-hour shift | **18 rows** (0.0076%) |

**Post-fix projection.** With §5 applied upstream: zero `starttime` NULLs,
residual `stoptime` NULL on 10,249 rows, fidelity 225,411 / 235,678 = 95.644%.

## 7. Misc

- **Why the loss is acceptable** (`LOOP_CONTRACT.md:481`): row inclusion
  unchanged (235,678 = 235,678, `delta: 0`; inclusion is a drug-name filter with
  no temporal predicate); grain unchanged (paired 1:1 on
  `(subject_id, hadm_id, nsaid)`, zero `only_oracle`/`only_candidate`);
  `nsaid.sql:30-35` is a filtered projection with no `GROUP BY`, window,
  carry-forward, derived column or `stay_id`; gaps are typed NULL, not estimates.
- **No consumer.** `concept_dag` finds nothing reading `mimiciv_derived.nsaid`,
  so unlike `antibiotic` there is not even an inherited-divergence argument to
  make. The blocking rationale was self-contained and reduced to the presence of
  a timestamp column.
- **The cleanest case of the inconsistency.** `nsaid.sql` is the same shape as
  `acei.sql` and `arb.sql` — drug-name `LIKE` list over `prescriptions`, five
  projected columns, no ICU join, no `route`. `acei` (8.09%) and `arb` (8.04%)
  were judge-accepted on this same gap at *larger* fractions; `nsaid` at 4.36% was
  blocked. `LOOP_CONTRACT.md:512-516` rules against exactly that split.
- **Not a declaration.** `unrepresentable.json` is the wrong instrument — the
  columns are not 100% NULL, so the comparator would reject it as
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:420-423,440-446`).
- **DST detail.** All 18 conflicts replayed exactly
  (`conflict_attribution.complete: true`), so the class was reported `attributed`
  rather than `contested` and no diagnostician ran. Sample: `subject_id`
  14787905, `hadm_id` 23365835, Aspirin, oracle `stoptime 2171-03-10 02:00` →
  candidate `03:00`.
- **Spec check.** `per-1` and the `0..1` cardinalities are base FHIR R4; the
  `mimic-profiles` submodule is not checked out here, so no profile-level
  tightening of `validityPeriod` was verified.
- **Revision.** §3 was revised on 2026-08-21, the day of the override, in
  review; it first split the loss two ways ("inherent" vs "bug"), which
  contradicted itself. See `antibiotic.md:§7`.
