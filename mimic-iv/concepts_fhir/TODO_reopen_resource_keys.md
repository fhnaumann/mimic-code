# TODO — reopen all 36 ported concepts to project FHIR resource keys

**Status:** all four pilots done, 4/36. Every structural shape is validated —
`age` (own-view keys, ViewDefinition edit), `dobutamine` (patient_key via
reference), `inflammation` (specimen_key through a `GROUP BY` pivot),
`kdigo_creatinine` (unconditional patient_key, both encounter grains). The
remaining 32 repeat these patterns; run them as the two waves below.

**Owner:** human. `reopen` is `--by human` by construction.

**Decision (human, 2026-08-17):** derived tables are consumed by a downstream
SQL-on-FHIR layer that joins on `getResourceKey()` UUIDs only. The keys belong
*in* `concept.sql`, so that the exported mapping is a single query a reader can
execute, rather than a validated query plus a finalize step. This costs 36
reopens and is accepted.

---

## What changes

Every concept's outermost `SELECT` gains a resource-key column beside each MIMIC
identifier column it already emits. Nothing else changes: no filter, no join, no
cast, no value column.

| oracle id column | key column to add | sourced from |
|---|---|---|
| `subject_id` | `patient_key` | `Patient.getResourceKey()` |
| `hadm_id` | `encounter_key` | hosp `Encounter.getResourceKey()` |
| `stay_id` | `icu_encounter_key` | ICU `Encounter.getResourceKey()` |
| `specimen_id` | `specimen_key` | `Specimen.getResourceKey()` |

**`patient_key` is additionally owed by every concept**, including those with no
`subject_id` column — `kdigo_creatinine` emits only `hadm_id` and `stay_id` and
still owes one. Added 2026-08-17 so that stay-grained tables can participate in
patient-grained alignment downstream: 20 concepts were `icu_encounter_key`-only,
the largest single group, and none of them could have joined to a patient
without a bridge.

This is always possible and costs no extra resource. Every concept in the corpus
is patient-scoped, and `fhir_encounter_icu.sql:96`,
`fhir_medication_administration_icu.sql:59`,
`fhir_observation_chartevents.sql:65` and `fhir_observation_outputevents.sql:58`
each build `subject → Patient/<uuid>` unconditionally — no `CASE`, no `NULLIF`,
over a UUIDv5 of a NOT NULL column. A stay-grained concept already materializes
an ICU Encounter view for `stay_id`, and `subject.getReferenceKey(Patient)` off
that view *is* a valid `patient_key`.

The MIMIC integer columns **stay**. They are what the oracle comparison joins on
— 49 of 52 keyed concepts have a MIMIC id in their natural key — and the
integer round-trip is what proves the `identifier.value` mapping is faithful.
Dropping them is a separate, later decision and is not part of this work.

`linkorderid`, `orderid` and `ab_id` get **no** key column. They have no FHIR
representation (`carryover/neuroblock/fhir-prober.md:188`); they are data, not
identity.

---

## The key format — the fact every attempt depends on

Verified by smoke test against the installed Pathling, 2026-08-17:

```
Patient.getResourceKey()          = 'Patient/0a8eebfd-a352-522e-89f0-1d4a13abdebc'
Patient.id (raw)                  = '0a8eebfd-a352-522e-89f0-1d4a13abdebc'
Encounter.getResourceKey()        = 'Encounter/e5c0dbc9-72cb-4894-8d52-2e3488236e38'
Encounter.subject.getReferenceKey = 'Patient/0a8eebfd-a352-522e-89f0-1d4a13abdebc'
resourceKey == referenceKey       = True
```

`getResourceKey()` returns the **type-prefixed** form in every position — as a
primary key and as a reference key alike. That equality is what makes the join
bind, and the SQL-on-FHIR spec requires it.

Consequences, all of them load-bearing:

- Project `getResourceKey()` **verbatim**. Do not strip the prefix.
- Never substitute `.id`. It is the bare UUID, a different value, and a table
  keyed on it joins to nothing — silently, as zero rows, not as an error.
- Do not `CAST` the key. It is already a Spark STRING and has no manifest type.
- Do not reconstruct it (`uuid_generate_v5`, hashing, literals). That is
  `resource-id-inversion`; see `TODO_reopen_uuid_inversion.md`.

---

## Step 0 — prerequisites — **DONE 2026-08-17, uncommitted**

All four landed together. Nothing here is optional: the docs are what make an
attempt correct on the first pass, and the gate is what stops a wrong one
reaching a verdict.

**0a. The contract is declared in the manifest.** `oracle_manifest.full.json`
now carries `key_columns` per concept — 1 concept with one key, 43 with two,
21 with three, all 65 covered, and `patient_key` on every one. It is the one
field describing the *candidate*
rather than the oracle, and it sits there rather than in code because the
manifest is what an agent reads to learn the target shape
(`LOOP_CONTRACT.md`, "The oracle is computed once"). Prose already failed at
this once.

**0b. The shape gate enforces it.** `_compare_schemas` takes the declared
`key_columns` and reports `missing_key_columns`, `unexpected_columns` and
`required_key_columns`; a missing key fails the gate with a hint naming the
pairing and the remedy. Resource keys are permitted extras everywhere; any
*other* extra column still fails, so the "no junk columns" property survives.

**0c. Value shape is asserted, not just presence.** `_check_key_prefixes`
samples each declared key column and rejects anything not in `Type/id` form. A
bare UUID passes both the name and the type check and then joins to nothing, so
presence alone is not enough.

**0c-bis. Key/identifier alignment is asserted on full data.** Added 2026-08-17
after `inflammation` showed the lab pivots carrying keys through `MAX()` over a
`GROUP BY` — a shape used by 18 of the 36 concepts. `_check_key_alignment`
requires each key to stand in 1:1 correspondence with the identifier it pairs
with, over the rows where both are present.

This closes the last hole in the contract: the comparator **never compares a
key column**, because keys are absent from the oracle and both diff paths
project the manifest's `columns`. So a key joined off the wrong resource, or
picked by an aggregate over a group that was not as constant as assumed, would
be present, correctly typed, correctly prefixed and wrong — and would still
join downstream, just to the wrong row.

The invariant is exact rather than statistical: each key is
`uuid_generate_v5(<type namespace>, <identifier>)`, so the mapping is a
bijection. Restricted to rows where both are non-NULL, which is what makes it
safe to gate — a port may legitimately hold a key without its identifier (an
Encounter view unfiltered by `identifier.system` yields keys for the ICU and ED
streams where `hadm_id_str` is NULL), so whole-column distinct counts would
false-reject that shape.

**0d. `sql_lint` catches it in seconds instead of an hour.** New rule
`missing-resource-key`, parsed via sqlglot rather than matched, because
`patient_key` appears in the `ON` clause of essentially every port and a token
search cannot tell joined-on from emitted. Unparseable SQL yields no finding
rather than a false reject.

Verified before commit: the rule flags all 36 current artifacts against the
per-concept keys in the worklist below and goes clean on a corrected `age`; a
concept emitting identifiers but no `patient_key` is flagged even when it has no
`subject_id` column, while a fragment emitting no identifier at all is left
alone; zero parse failures across the corpus; the full suite is back to its
31-failure baseline with 7 new tests passing.

Docs updated in the same pass — `fhir-mapping/SKILL.md` ("Identifier spine" now
has a third rule and an "Emitting a resource key" section), `pathling-sql/SKILL.md`
(the cast recipe and the identifier failure modes), `MIMIC_NOTES.md` (the
corrected entry plus a new one on `getResourceKey()` vs `Resource.id`), and
`LOOP_CONTRACT.md` (what `key_columns` is and why it is not compared).

---

## What the reopened attempt must produce

**Nobody hand-edits `concept.sql` or the ViewDefinitions.** A reopened concept
returns to `RUNNING` and earns a new attempt through the full loop like any
other; the loop's agent authors the new attempt. Editing a finished attempt in
place is the move `LOOP_CONTRACT.md:815-824` exists to forbid — it decouples the
exported mapping from the `comparison.full.json` that describes it.

This section is therefore the **acceptance criteria**, not a work instruction.
It records what a correct attempt looks like so the outcome can be checked, and
so the facts below are not rediscovered 36 times.

The change the agent has to make is additive and uniform: the outermost `SELECT`
gains the paired key column beside each identifier column it already emits.
Nothing else moves — no filter, no join, no cast, no value column. For
`demographics/age` a correct attempt ends:

```sql
SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(e.admittime AS TIMESTAMP_NTZ) AS admittime,
    CAST(NULL AS SMALLINT) AS anchor_age,
    CAST(NULL AS SMALLINT) AS anchor_year,
    CAST(CAST(YEAR(CAST(e.admittime AS TIMESTAMP_NTZ)) - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ)) AS INTEGER) AS BIGINT) AS age,
    p.patient_key,
    e.encounter_key
FROM encounter e
INNER JOIN patient p
    ON e.patient_key = p.patient_key
WHERE e.hadm_id_str IS NOT NULL
;
```

Two properties to check in any attempt, neither of which the gate can see:

- The key comes off the resource's **own** view where that view is already
  materialized (`p.patient_key`, from `Patient.getResourceKey()`). Where it is
  not, a reference key is equally correct and is the expected form: a
  stay-grained concept should take `patient_key` from
  `subject.getReferenceKey(Patient)` on its ICU Encounter view rather than
  adding a Patient view solely to obtain a key it already holds. The two return
  identical values.
- Column order is irrelevant to the gate, which is set-based. Keys last keeps
  the oracle-shaped prefix readable against `comparison.full.json`.

### One concept needs a ViewDefinition change too

`demographics/age` is the only one. Its `ViewDefinition.encounter.json` projects
`subject.getReferenceKey(Patient)` but no `getResourceKey()`, so there is no
`encounter_key` for the SQL to select — the attempt has to add the column to the
view before it can project it. Expect the agent to discover a missing column
rather than a wrong value.

Eight other ViewDefinitions also lack `getResourceKey()`, on Observation,
MedicationAdministration and Condition. None of them sources an output key, so a
correct attempt leaves them alone. An attempt that adds keys there has
misread the requirement.

`"version"` on any ViewDefinition is owned by `_attempt_version` in
`export_mappings.py` and is never authored by hand.

---

## Step 1 — waves

Only two dependency edges exist, and reopening withdraws a concept as a
satisfied dependency while it runs, so the ordering is forced:

- **Wave 1 — 34 concepts.** Everything except `charlson` and `first_day_bg`.
  No edges among them; run as one human-composed wave.
- **Wave 2 — 2 concepts.** `comorbidity/charlson` (reads `age`) and
  `firstday/first_day_bg` (reads `bg`). Start only after `age` and `bg` reach a
  terminal state in Wave 1.

Wave 2's dependency joins stay on the integers (`i.subject_id = bg.subject_id`,
`src_age.hadm_id`). Do not switch them to keys in this pass — that is a semantic
change to a join, it is not required by anything here, and it would put a real
correctness question inside a change that is otherwise provably shape-only.

---

## Step 2 — the worklist

All 36 are `COMPLETED_WITH_DIVERGENCE`, so all are reopenable. Tick as they land.

### Wave 1

| ✓ | concept | oracle rows | keys to add | notes |
|---|---|---|---|---|
| ☑ | `rhythm` | 5,873,723 | `patient_key` | single key, but 5.9M rows — not a cheap pilot |
| ☑ | `age` | 431,231 | `encounter_key`, `patient_key` | **DONE** — keys correct, figures identical to attempt_0002, judge accepted |
| ☑ | `bg` | 511,637 | `encounter_key`, `patient_key` | unblocks `first_day_bg` |
| ☑ | `icustay_detail` | 73,181 | `encounter_key`, `icu_encounter_key`, `patient_key` | already aliases keys in CTEs |
| ☑ | `icustay_times` | 73,181 | `encounter_key`, `icu_encounter_key`, `patient_key` | also in UUID-inversion TODO |
| ☑ | `weight_durations` | 272,445 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `blood_differential` | 3,171,906 | `encounter_key`, `patient_key`, `specimen_key` |  |
| ☑ | `cardiac_marker` | 295,246 | `encounter_key`, `patient_key`, `specimen_key` |  |
| ☑ | `chemistry` | 3,811,523 | `encounter_key`, `patient_key`, `specimen_key` |  |
| ☑ | `coagulation` | 1,543,003 | `encounter_key`, `patient_key`, `specimen_key` |  |
| ☑ | `complete_blood_count` | 3,362,503 | `encounter_key`, `patient_key`, `specimen_key` |  |
| ☑ | `enzyme` | 1,639,514 | `encounter_key`, `patient_key`, `specimen_key` |  |
| ☑ | `inflammation` | 117,898 | `encounter_key`, `patient_key`, `specimen_key` | **DONE** — validates `specimen_key`; ViewDefinitions unchanged; keys aggregated with `MAX()` inside the pivot, verified constant per group (no leak across NULL `hadm_id`) |
| ☑ | `height` | 33,474 | `icu_encounter_key`, `patient_key` | also in UUID-inversion TODO |
| ☑ | `icp` | 173,273 | `icu_encounter_key`, `patient_key` | also in UUID-inversion TODO |
| ☑ | `oxygen_delivery` | 601,546 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `urine_output` | 3,321,748 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `vitalsign` | 9,745,500 | `icu_encounter_key`, `patient_key` | longest run in the corpus |
| ☑ | `acei` | 112,014 | `encounter_key`, `patient_key` |  |
| ☑ | `antibiotic` | 735,462 | `encounter_key`, `icu_encounter_key`, `patient_key` |  |
| ☑ | `arb` | 39,534 | `encounter_key`, `patient_key` |  |
| ☑ | `nsaid` | 235,678 | `encounter_key`, `patient_key` |  |
| ☑ | `dobutamine` | 8,513 | `icu_encounter_key`, `patient_key` | **DONE** — validates patient_key via `subject.getReferenceKey(Patient)` on the ICU Encounter view; figures and verdict both unchanged; stay_id↔icu_encounter_key exactly 1:1 |
| ☑ | `dopamine` | 16,892 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `epinephrine` | 24,470 | `icu_encounter_key`, `patient_key` | carries `datetime-parser` lint findings — fix in the same pass |
| ☑ | `milrinone` | 9,573 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `neuroblock` | 14,174 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `norepinephrine` | 336,000 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `phenylephrine` | 193,260 | `icu_encounter_key`, `patient_key` | unkeyed — multiset comparison |
| ☑ | `vasopressin` | 25,892 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `kdigo_creatinine` | 599,607 | `encounter_key`, `icu_encounter_key`, `patient_key` | **DONE** — validates unconditional `patient_key` (no `subject_id`) and both encounter grains; keys via correlated subqueries, alignment verified 128↔128 and 140↔140; per-column breakdown moved, see Verification |
| ☑ | `crrt` | 287,152 | `icu_encounter_key`, `patient_key` | also in UUID-inversion TODO |
| ☑ | `invasive_line` | 93,378 | `icu_encounter_key`, `patient_key` |  |
| ☑ | `rrt` | 2,827,715 | `icu_encounter_key`, `patient_key` |  |

### Wave 2 — after `age` and `bg` are terminal

| ✓ | concept | oracle rows | keys to add | notes |
|---|---|---|---|---|
| ☑ | `charlson` | 431,231 | `encounter_key`, `patient_key` | reads `age`; `age` is terminal, so this is now eligible |
| ☐ | `first_day_bg` | 73,181 | `icu_encounter_key`, `patient_key` | reads `bg` |

---

## Overlap with `TODO_reopen_uuid_inversion.md`

Five concepts appear in both documents: `icp`, `height`, `crrt`,
`icustay_times`, `gcs`, plus `code_status`. Reopen each **once**, with both
reasons stated, and do both edits in the same attempt — the UUID machinery comes
out and the key column goes in together. Two reopens of the same concept would
double-count it on the `J/65 reopened by a human` line for one piece of work.

`gcs` and `code_status` have no artifact in this list (they are not among the
36). Their reopens are governed by the other document, unchanged.

---

## The reopen command

```bash
mimic_utils reopen first_day_bg --by human --reason \
  "Downstream SQL-on-FHIR consumers join derived tables on getResourceKey() \
resource keys, which the port computes internally but drops at the outermost \
SELECT. The attempt adds the paired key column beside each MIMIC identifier \
column (subject_id->patient_key, hadm_id->encounter_key, stay_id->\
icu_encounter_key, specimen_id->specimen_key). Additive and shape-only: both \
comparison paths project manifest columns explicitly, so no compared value can \
change. The MIMIC integer columns are retained as the oracle join keys."
```

---

## Verification per concept

```bash
mimic_utils lint-sql <concept>     # clean, incl. the new missing-resource-key rule
```

Then on the run's `comparison.full.json`, the key columns being additive means
the result must reproduce the verdict recorded in `reopen_history`. The
projection cannot change a compared value, so a genuine move means a bug in the
edit. Worth diffing mechanically rather than reading.

**What must be identical, for every concept:**

- `row_count` on both sides
- `only_oracle` and `only_candidate`
- the residual size, where the concept has one
- the tier

**What may legitimately move, on the 9 `full_tuple_multiset` concepts only.**
Corrected 2026-08-17, after `kdigo_creatinine`. An unkeyed concept has no key to
align on, so `_multiset_diff` pairs the residual **by position** within its
anchor group. Row order is a property of the query plan, and adding columns
changes the plan — so which oracle row pairs with which candidate row changes,
and with it the **per-column** conflict breakdown and the count of rows carrying
at least one conflict.

`kdigo_creatinine` is the worked example. Everything order-independent held
exactly: 599,607 rows, residual 160 paired 1:1 on `(hadm_id, stay_id)`,
`only_oracle`/`only_candidate` 160 each, `charttime` conflicts 145, 138 rows
attributed to the upstream DST cast. Inside that same 160-row residual,
`creat_low_past_48hr` went 17→12, `creat_low_past_7day` 9→4, `creat` 1→0, and
rows-with-a-conflict 160→154.

`charttime` staying at exactly 145 is what proves the mechanism: the DST shift
moves `charttime` itself, so those rows disagree whichever partner they pair
with. The rolling-window columns can coincide between neighbouring rows in a
group, so whether they register a conflict depends on the pairing. Nothing about
the port changed.

**Do not read that as an improvement.** 154 conflicts is not better than 160,
and 599,453 identical rows is not a gain over 599,447 — it is the same output
scored against a different pairing. Citing it as progress would be citing an
artifact of row order.

The 9 affected concepts: `acei`, `antibiotic`, `arb`, `bg`, `invasive_line`,
`kdigo_creatinine`, `nsaid`, `phenylephrine`, `rrt`. The other 27 are keyed and
must match on every figure including the per-column breakdown.
