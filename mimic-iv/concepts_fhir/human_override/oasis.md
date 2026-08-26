# `oasis` — human override out of `BLOCKED_REPRESENTATION`

- **Applied:** 2026-08-26
- **Decision:** override — the block is cleared
- **Transition:** `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, `--by human`
- **Attempt:** `concepts/score/oasis/attempt_0002`
- **Canonical SQL:** `mimic-iv/concepts/score/oasis.sql`
- **Fidelity:** 73,127 / 73,181 stays identical (99.9262%), row counts equal

A different class from the `sofa` / `first_day_sofa` overrides of the same day.
Those rest on a Pathling encoder constant that no `mimic-fhir` patch can lift.
This one is an ordinary upstream ETL omission — `mimiciv_hosp.services` is read
in exactly one place in all of `mimic-fhir`, and only its first row survives.
That makes it *repairable in principle*, which under
`human_override/README.md:79-84` strengthens the override rather than weakening
it: the override rests on what is recoverable from what is served **today**, and
on what the absence reaches.

## 1. The problem

54 of 73,181 ICU stays (0.0738%) come back with `electivesurgery = 0` /
`electivesurgery_score = 6` where the oracle holds `1` / `0`, and with the
resulting six-point difference in `oasis` and its `oasis_prob`. Four columns,
the same 54 rows, no other divergence class: row counts equal, 0 `only_oracle`,
0 `only_candidate`, 0 `differing_null_only`, and the other 21 compared columns
identical on all 73,181 rows.

The equivalence judge ruled **`blocked`**
(`attempt_0002/evidence/equivalence-judge.md`), having agreed the cause is
upstream and not a port defect:

> The judge found the loss essential: it changes the row-level elective flag,
> the six-point OASIS component, total OASIS, and clinically meaningful
> mortality probability (`mimic-iv/concepts/score/oasis.sql:91-97,197-199,255-275`).
> Selective NULLs cannot isolate the affected rows. […] The judge therefore
> required `BLOCKED_REPRESENTATION`, not acceptance or another retry.

Every factual finding in that paragraph is confirmed, including the
selective-NULL point (§7). What is rejected is the inference from "changes a
six-point component and a mortality probability" to *essential*. That is the
clinical-importance test, and `LOOP_CONTRACT.md:481-491` rules it out in terms:
an absence is essential only if it changes row inclusion, the grain, grouping,
carry-forward, or contaminates values that *are* representable — "**test what the
absence reaches, not whether it sounds clinically important**." Applied term by
term (§7), this absence reaches none of the five.

## 2. What caused it

**One statement, and it is the only place `mimic-fhir` reads the services
table.** `mimic-fhir/sql/fhir_encounter.sql:45-57`:

```sql
), first_service AS (
    WITH services AS (
        SELECT
            hadm_id
            , curr_service
            , ROW_NUMBER() OVER (PARTITION BY hadm_id ORDER BY transfertime ASC) row_num
        FROM mimiciv_hosp.services s
    )
    SELECT
        hadm_id
        , curr_service
    FROM services
    WHERE row_num = 1
),
```

It ranks every service transfer for an admission by `transfertime` and keeps
`row_num = 1`. `transfertime` itself is projected only inside the window
function and is never selected. That one row is carried at
`fhir_encounter.sql:71` (`, serv.curr_service AS serv_CURR_SERVICE`), joined at
`:83-84`, and written as a single coding at `:142-147`:

```sql
, 'serviceType', jsonb_build_object(
    'coding', jsonb_build_array(json_build_object(
        'system', 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-services'
        , 'code', serv_CURR_SERVICE
    ))
)
```

So the served `Encounter` carries **the earliest service code and no service
times**, for every admission and unconditionally.

Canonical OASIS needs the whole history inside a window
(`mimic-iv/concepts/score/oasis.sql:32-43`):

```sql
WITH surgflag AS (
    SELECT ie.stay_id
        , MAX(CASE
            WHEN LOWER(curr_service) LIKE '%surg%' THEN 1
            WHEN curr_service = 'ORTHO' THEN 1
            ELSE 0 END) AS surgical
    FROM `physionet-data.mimiciv_icu.icustays` ie
    LEFT JOIN `physionet-data.mimiciv_hosp.services` se
        ON ie.hadm_id = se.hadm_id
            AND se.transfertime < DATETIME_ADD(ie.intime, INTERVAL '1' DAY)
    GROUP BY ie.stay_id
)
```

`MAX(...)` over every service with `transfertime < intime + 1 day`. The served
data can supply one term of that aggregate and cannot supply the predicate at
all. A stay whose first service is medical and whose second, still before the
cutoff, is surgical is indistinguishable — in FHIR — from one that never went to
surgery.

**No alternative carrier.** `grep -rn "mimiciv_hosp.services" mimic-fhir/sql/`
returns three hits: `fhir_encounter.sql:51` above, and
`codesystem/cs-services.sql:11` with `codesystem/vs-descriptions.sql:42`, which
build the `mimic-services` CodeSystem/ValueSet from `SELECT DISTINCT` over the
table — the vocabulary of service codes, carrying no `hadm_id` and no patient
link. Element by element on the resource that could plausibly have held it:

- **`Encounter.serviceType`** — the element itself, and in R4 it is `0..1`. The
  build is R4 (`fhir_encounter.sql:153` writes `hospitalization`, renamed in R5),
  so a conformant second service cannot go here at all. One coding is written,
  and the port already reads *all* codings that exist
  (`attempt_0002/ViewDefinition.hospital_service.json`, `forEach:
  "serviceType.coding"`), so a fuller `serviceType` would need no port change.
- **`Encounter.location`** — built from `mimiciv_hosp.transfers.careunit` with
  per-location periods (`fhir_encounter.sql:7-26`, written at `:171`). This is a
  *ward* history, not a *service* history: `Med/Surg`, `Vascular`,
  `Surgical Intensive Care Unit (SICU)` are physical units, and
  `services.curr_service` is the admitting team. Inferring one from the other is
  an estimate, not a recovery, and attempt 0001 measured what that costs — an
  `AMB`-based heuristic produced 3,349 conflicts, of which 3,295 were false
  positives (`MIMIC_NOTES.d/oasis.md`).
- **`Encounter.type`** — occupied by `mimiciv_hosp.hcpcsevents` HCPCS codes
  (`fhir_encounter.sql:27-43`, written at `:123-134`), with a SNOMED
  `308335008` placeholder when the admission has none. Billed procedure codes
  are a different clinical fact with different coverage; reading surgery out of
  them is again an estimate.
- **`Encounter.priority`** — carries the elective half of the predicate exactly
  and is already used. `admission_type = 'ELECTIVE'` maps uniquely to `EL` via
  `mimic-fhir/sql/fhir_etl/map_encounter_priority.sql:14`, written at
  `fhir_encounter.sql:135-141`, read at `attempt_0002/concept.sql:92-99`. This
  is what took attempt 0001's 3,349 conflicts down to 54.
- **`class`, `period`, `hospitalization`, `serviceProvider`, ICU `Encounter`** —
  all carry their own source columns exactly and none carries service history.
  `fhir_encounter_icu.sql` writes no `serviceType` at all; `MIMIC_NOTES.d/oasis.md`
  measured ICU `serviceType` population at 0/140.
- **Resource ids** — opaque `uuid_generate_v5` values. Inversion is refused by
  `LOOP_CONTRACT.md:396-401` and by `src/mimic_utils/sql_lint.py`, and would
  recover identity rather than a dropped `curr_service` in any case.

## 3. Intentional or a bug?

Ruled per class. Two things are lost by the one statement, and they grade
differently.

| class | what is lost | verdict |
|---|---|---|
| 1 | every `services.curr_service` row after the first — the service *history* | **repairable, but not by a one-line change.** R4 `Encounter.serviceType` is `0..1`, so a conformant fix needs a new carrier (extension, `EpisodeOfCare`, or R5). Upstream's choice is a defensible reading of the element, not a mistake — the middle tier of `human_override/README.md:69-77`. |
| 2 | `services.transfertime`, for every service including the retained one | **plain omission.** Nothing in the IG blocks a period beside the service; the value is already in scope in the CTE at `:50` and simply not selected. This one is closer to a bug, and it is the reason the port cannot apply the canonical `< intime + 1 day` window even in the single-service case. |
| 3 | nothing else | `priority`, `class`, `type`, `period`, `location`, `hospitalization` each carry their source value exactly (§2). |

Class 1 produces all 54 observed rows. Class 2 produces none of them *in this
comparison* but is a live second failure mode in the opposite direction: a
retained first service that is surgical but transfers **after** `intime + 1 day`
would give the oracle `0` and the port `1`. Zero such rows occur in the full
comparison — all 54 conflicts are candidate `0` / oracle `1` — so class 2 is a
latent hazard here, not a measured loss.

Note which way the grading cuts, per `human_override/README.md:79-84`. Calling
class 1 repairable does not weaken this override; it means the block is a
standing cost with a filable remedy (§5), while the accept rests on §2 (nothing
recoverable from today's served data) and §7 (the absence reaches nothing
essential).

## 4. Example of the loss

The first sampled conflict row, from `attempt_0002/comparison.full.json`
(`diff.samples.differing_conflict[0]`) — every non-elective column identical:

| | `stay_id` | `hadm_id` | `age` | `gcs` | `mechvent` | `urineoutput` | `electivesurgery` | `electivesurgery_score` | `oasis` | `oasis_prob` |
|---|---|---|---|---|---|---|---|---|---|---|
| **relational MIMIC-IV (oracle)** | 33872226 | 29802872 | 69 | 15.0 | 1 | 2870.0 | **1** | **0** | **23** | **0.03761** |
| **port over MIMIC-on-FHIR** | 33872226 | 29802872 | 69 | 15.0 | 1 | 2870.0 | **0** | **6** | **29** | **0.07748** |

All nine other component scores agree exactly (`age_score` 6, `preiculos_score`
2, `gcs_score` 0, `heart_rate_score` 1, `mbp_score` 2, `resp_rate_score` 1,
`temp_score` 2, `urineoutput_score` 0, `mechvent_score` 9). The served hospital
`Encounter` for `hadm_id` 29802872 carries one service coding and the elective
priority:

```json
{ "resourceType": "Encounter",
  "priority":    { "coding": [ { "system": ".../v3-ActPriority",       "code": "EL" } ] },
  "serviceType": { "coding": [ { "system": ".../CodeSystem/mimic-services", "code": "MED" } ] } }
```

`MED` is the first service by `transfertime`; the surgical service that follows
it before `intime + 1 day` is in `mimiciv_hosp.services` and in no FHIR
resource. `oasis.sql:92-97` needs `ELECTIVE AND surgical = 1`; the port sees
`EL AND surgical = 0` and scores the component 6 instead of 0. The second
sampled row (`stay_id` 34996424, `hadm_id` 27687402) is the same shape: `oasis`
26 against the oracle's 20, every other component equal.

## 5. What a fix would look like

Class 3 needs nothing. Classes 1 and 2 are one `mimic-fhir` PR, and the ETL
already contains the pattern it needs — `transfer_locations`
(`fhir_encounter.sql:7-26`) aggregates a full history with per-entry periods via
`jsonb_agg`, so this is a shape the build already emits.

`Encounter.serviceType` being `0..1` in R4 is the only real obstacle, and it
rules out the obvious patch (appending codings). Three conformant routes, in
increasing cost:

1. **A MIMIC extension on `Encounter`**, one repetition per service, each with
   the `mimic-services` coding and the `transfertime` — the direct analogue of
   `transfer_locations`, and the cheapest thing to file. It fixes classes 1 and 2
   together, and the profile already carries MIMIC-specific extensions elsewhere.
2. **One `EpisodeOfCare` per service**, referenced from the `Encounter`, with
   `period.start = transfertime`. More faithful to the FHIR model and a larger
   change: a new resource type, a new namespace, a new ndjson stream.
3. **Move to R5**, where `Encounter.serviceType` is `0..*`. Correct and out of
   scope for a PR against the current build.

Under route 1 the §4 example re-serves as:

```json
{ "resourceType": "Encounter",
  "priority":    { "coding": [ { "code": "EL" } ] },
  "serviceType": { "coding": [ { "code": "MED" } ] },
  "extension": [
    { "url": ".../StructureDefinition/encounter-service-history",
      "extension": [ { "url": "service", "valueCodeableConcept": { "coding": [ { "code": "MED"  } ] } },
                     { "url": "transferTime", "valueDateTime": "…" } ] },
    { "url": ".../StructureDefinition/encounter-service-history",
      "extension": [ { "url": "service", "valueCodeableConcept": { "coding": [ { "code": "SURG" } ] } },
                     { "url": "transferTime", "valueDateTime": "…" } ] } ] }
```

and the port's `surgflag` (`attempt_0002/concept.sql:26-34`) becomes the
canonical `MAX(...)` over that extension with the `< intime + 1 day` predicate
restored — producing `electivesurgery = 1`, `electivesurgery_score = 0`,
`oasis = 23`, `oasis_prob = 0.03761`: the oracle row exactly. All 54 rows close,
and the class 2 hazard closes with them. **No port-side fix exists in the
meantime**, and that was measured rather than assumed: attempt 0001 recorded
3,349 conflicts using an `AMB`-class heuristic for the elective half, attempt
0002 replaced it with the exact `priority = EL` mapping and recorded 54. The
remaining 54 are not a heuristic's error — they are rows where the discriminating
source value is not served.

## 6. Numbers

From `attempt_0002/comparison.full.json`:

| | rows | of 73,181 |
|---|---|---|
| identical | 73,127 | 99.9262% |
| `differing_conflict` | 54 | 0.0738% |
| `differing_null_only` | 0 | — |
| `only_oracle` / `only_candidate` | 0 / 0 | — |
| `excluded_as_unrepresentable` | 0 columns | — |

Row counts: oracle 73,181, candidate 73,181, delta 0, `match: true`. Schema
`match: true` — 0 missing, 0 unexpected, 0 incompatible types; the three extra
columns are the required key columns `encounter_key`, `icu_encounter_key`,
`patient_key`. `identical_fraction` 0.999262; no declaration was made, so
`representable_fraction` equals it.

Per column — the only four that differ, all on the same 54 rows:

| column | conflicts | of 73,181 |
|---|---|---|
| `electivesurgery` | 54 | 0.0738% |
| `electivesurgery_score` | 54 | 0.0738% |
| `oasis` | 54 | 0.0738% |
| `oasis_prob` | 54 | 0.0738% |

Against the previous attempt (`MIMIC_NOTES.d/oasis.md`, attempt 0001 full
comparison): 3,349 elective-surgery conflicts → **54**, a 98.4% reduction, from
replacing the heuristic with `priority = EL`.

By the §3 classes: class 1 accounts for all 54 rows; class 2 for 0 of them
(latent, direction not exercised); class 3 for none. **No post-fix projection
beyond §5** — route 1 closes all 54, and until a route lands these figures are
terminal.

Direction is uniform: all 54 are candidate `electivesurgery = 0` /
`electivesurgery_score = 6` against oracle `1` / `0`. The diagnostician's
source-side accounting closed **54 of 54** against the full oracle and
`mimiciv_hosp.services`, spanning **51 admissions**
(`attempt_0002/evidence/mismatch-diagnostician.md`).

Classification `keyed`, key `(stay_id)`, tier `contested`,
`judge_required: true`, `diagnostician_required: true`. Comparator tolerances:
relative `0.001`, absolute `1e-9`, timestamps 1 s, row count exact.
`conflict_attribution.attempted` is `false` — `"no datetime column in this
concept; the DST cast cannot apply"` — so the comparator ran no mechanical
replay here and the 54-row attribution is the diagnostician's source-side
accounting, which is complete at 54/54 rather than sampled.

## 7. Misc

- **Why the loss is acceptable** (`LOOP_CONTRACT.md:481-491`), term by term.
  *Row inclusion:* unchanged — 73,181 = 73,181, `only_oracle` and
  `only_candidate` both 0; the cohort is every ICU stay, with no service
  predicate. *Semantic grain:* unchanged — paired 1:1 on `stay_id`.
  *Grouping:* unchanged — the port's `surgflag` is the canonical `MAX` over the
  services it is given (`attempt_0002/concept.sql:26-34`); no `GROUP BY` differs.
  *Temporal carry-forward:* none — OASIS is one row per stay with no window over
  other rows, so a divergent row cannot propagate to a second one. This is the
  term that moved in the `sofa` override and does not move here. *Contamination
  of representable values:* none — no estimate, no imputation, no NULL for a
  value; every affected cell holds a well-defined integer or probability, and the
  other 21 columns are exact on all 73,181 rows including the 54. The absence
  reaches none of the five.
- **The judge's selective-NULL point is confirmed, and it is worth stating why,
  because it nearly goes the other way.** The port *can* see the at-risk set:
  stays with `priority = EL` whose one served service is non-surgical. It cannot
  see which members of that set have a later surgical service. A typed NULL
  across the set would, on these 54 rows, make `electivesurgery` and
  `electivesurgery_score` `differing_null_only` **and** make `oasis` /
  `oasis_prob` match the oracle exactly, because canonical
  `oasis.sql:255-275` folds the component through `COALESCE(electivesurgery_score, 0)`
  and the oracle's own contribution on these rows is 0. That is a real
  improvement on 54 rows. It is paid for on every *other* at-risk row — where the
  oracle scores the component 6 and a NULL folds to 0 — turning each into a fresh
  6-point `oasis` conflict. The trade is favourable only if the at-risk set is
  not materially larger than 54, and elective medical admissions with no
  surgical service plainly exist, so it is not. **This was reasoned, not
  measured**, and the measurement is cheap: on `/scratch3`, count stays with
  `admission_type = 'ELECTIVE'` whose first service by `transfertime` is
  non-surgical. If that count came back at or near 54, the correct move would be
  `retry`, not this override. A reader should know that is the one open check.
- **The demo cannot exhibit this at all.** Probed directly against
  `~/warehouses/mimic4-demo.db` on 2026-08-26: of 140 demo ICU stays, 5 are
  `ELECTIVE`, and all 5 have a surgical first service — 0 at-risk stays, 0
  flipped. The demo gate could not have caught this and did not fail; the event
  is full-data-only, which is why it first appears in attempt 0001's full run.
- **Consistency with `sapsii` and `apsiii`, which are `COMPLETED` exact.**
  `sapsii` reads the *same* truncated element and is unaffected by design:
  `sapsii.sql:61-75` ranks services by `transfertime` and `:349` joins
  `sf.serviceorder = 1` — the first service, which is precisely the one row
  `fhir_encounter.sql:57` retains. The upstream truncation is invisible to it.
  So there is no split verdict on the same evidence: the two concepts ask
  different questions of the same element, and one of them is answerable from
  what is served. Blocking `oasis` while `sapsii` is exact would not be
  inconsistent — but it would publish a table asserting that the loop can port
  OASIS only if the canonical query happens to want the first service.
- **Consistency with the divergent dependencies.** `age` and
  `first_day_vitalsign` are both `COMPLETED_WITH_DIVERGENCE (judge)`. The
  diagnostician verified that no residual OASIS column traceable to either
  differs, and neither feeds the elective branch: `age`/`age_score` agree on all
  54 sampled conflict rows, as do every vital-sign component. So this residual
  is `oasis`'s own inherited loss from `Encounter.serviceType`, not carried
  through a dependency, and `LOOP_CONTRACT.md:1002-1035` (wholly inherited
  divergence is `accept`) is *not* the ground for this override — §2 and §7 are.
- **Not a declaration.** `unrepresentable.json` is the wrong instrument:
  `electivesurgery` is non-NULL on 73,181 rows and correct on 73,127 of them, so
  the comparator would reject the claim as
  `false_unrepresentable_declaration` (`LOOP_CONTRACT.md:440-446`).
- **What downstream inherits: nothing.** No concept in the DAG depends on
  `oasis` — it is a leaf severity score, as are `sapsii`, `apsiii` and `lods`.
  The block gated no other work, and this override unblocks no other concept. It
  buys one published row in the results table and nothing else, which is worth
  saying plainly: the cost of the block was low, and so is the benefit of
  lifting it.
- **The served-data fact is already recorded.** `MIMIC_NOTES.d/oasis.md` carries
  both entries — "`Encounter.serviceType` carries one service code, not the
  services history" and "`Encounter.priority` preserves elective admission, but
  `serviceType` preserves only the first service" — each with its own probe and
  counts. No new dataset-wide note was warranted by this override, and none was
  added.
- **Not in the 2026-08-21 rerun wave.** `TODO_upstream_fix_rerun.md` lists four
  defects left open upstream; service-history truncation is a fifth that was
  never in that document, because `oasis` attempt 0002 is a fresh port run on
  2026-08-26 against the already-rebuilt warehouses, not a replay awaiting one.
  If the §5 route 1 extension lands, `oasis` is a plain `replay`.
- **Provenance.** Every count in §6 is read from
  `attempt_0002/comparison.full.json`; the §4 row is
  `diff.samples.differing_conflict[0]` verbatim; the 51-admission figure and the
  54/54 source-side closure are the diagnostician's
  (`attempt_0002/evidence/mismatch-diagnostician.md`). The `mimic-fhir` and
  canonical SQL in §2 is quoted from the working trees at
  `/Users/nau025/Documents/mimic-fhir` and `mimic-iv/concepts/score/oasis.sql`.
  The demo figures in §7 are a direct DuckDB query, stated as demo-scale.
