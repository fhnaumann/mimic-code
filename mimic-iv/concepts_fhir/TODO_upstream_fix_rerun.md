# TODO — rerun every affected concept against the fixed MIMIC-on-FHIR build

**Status:** open, 2026-08-24. Working doc: delete it when the last wave lands
and the results table has been regenerated. Everything durable in here belongs
in `MIMIC_NOTES.md` (the served-data facts, already merged) or
`LOOP_CONTRACT.md` (the gate semantics, revised 2026-08-24).

Three upstream defects were fixed on 2026-08-21 and both warehouses rebuilt, so
**56 of the 57 ported concepts hold a verdict earned against data that no longer
exists** — every one but `age`, which was already re-run. **52 of them are in
scope**: 47 replays, 2 relints, and 3 re-implements. The other 4 are
deliberately left alone because their blocker is a defect that was *not* fixed,
so a rerun would re-earn the same verdict. This says exactly what to run.

## What was fixed

| defect | commit | what changed for a port |
|---|---|---|
| DST spring-forward wall times normalised +1h | `ade10fb` (#124) | FHIR tables now generated under UTC. Same paths, corrected values. |
| `Patient.birthDate` from `MIN(transfers.intime)` | `3048c88` (#126, #117) | now `MAKE_DATE(anchor_year,1,1) - anchor_age`. Same element, corrected value, better coverage. |
| `chartevents.value` dropped when `valuenum` set | `e7c326b` (#125) | the text is now in `Observation.component[].valueString`. **A new element** — a port must be re-authored to read it. |

**Still open upstream, deliberately:** `inputevents.orderid`/`linkorderid` (only
inside the opaque UUID), the hospital `poe`/`poe_detail` branch,
`inputevents.starttime` for non-rate administrations, ICU
`MedicationAdministration` Quantity decimal scale. A concept whose only
divergence is one of these will re-earn the same verdict, so it is not in scope.

**Both warehouses are already rebuilt.** Demo:
`/Users/nau025/warehouses/mimic-iv-demo/delta`, rebuilt 2026-08-24 11:06 (the
old NDJSON build is kept beside it as `mimic-iv-demo.old-ndjson-2026-08-24/`
plus a tarball). Full: `/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse` —
confirmed indirectly and conclusively by the pilot below.

**The oracle is untouched.** Relational MIMIC-IV 2.2 did not change, so
`/scratch3/nau025/oracle/mimic4-full.db` and
`oracle/oracle_manifest.full.json` stand. Nothing to rebuild, nothing to
regenerate.

## The pilot already ran, and it worked

`age` attempt_0004 is the same `concept.sql` as attempt_0003 — verified
byte-identical — re-run against the rebuilt full warehouse:

| | attempt_0003 | attempt_0004 |
|---|---|---|
| `differing_conflict` | 504 (460 `age`, 44 `admittime`) | **0** |
| `only_oracle` / `only_candidate` | 0 / 0 | 0 / 0 |
| `representable_fraction` | 0.998831 | **1.000000** |
| tier | `contested` | `gap_shaped` |
| verdict | review → accepted | review → accepted |

One artifact confirming both the DST and the birthDate fix, on full data, with
the query held constant. It stays `review` rather than `match` only because
`anchor_age`/`anchor_year` are declared unrepresentable and are therefore 100%
NULL by design — that declaration still holds (`birthDate` is still one date, so
the pair is still collapsed).

`age` needed no `replay` because it was reopened by hand before the verb
existed. It cost an implementer run to re-author a file that came out identical.
That is the overhead the rest of this plan avoids.

## Four routes

| route | count | what runs |
|---|---|---|
| **replay** | 47 | `mimic_utils replay` carries `concept.sql` + ViewDefinitions + `unrepresentable.json` forward byte-identical. No analyst, no prober, **no implementer**. Only a `review` result needs a session, and only for the judge. |
| **relint** | 2 | `milrinone`, `creatinine_baseline` — replayable in principle, but their SQL predates the resource-key lint. Reopen and add `patient_key`; change nothing else. |
| **re-implement** | 3 | `gcs`, `ventilator_setting`, `first_day_gcs` — the text moved into an element their SQL does not read. Full `/goal` with the prober invalidated. |
| **leave alone** | 4 | `code_status`, `dopamine`, `epinephrine`, `neuroblock` — blocker is an unfixed defect. |

Routing is mechanical, not a judgement call per concept:
`mimic_utils replay <c> --check` reads the concept's own
`unrepresentable.json` and recorded verdict against the registry in
`src/mimic_utils/replay.py`, **lints the SQL it would carry**, and refuses
anything a fix has made incomplete or a gate would now reject.

**The relint route was found by the preflight, not by reading**, which is the
whole argument for running `--check` over a wave before touching it. Both
concepts emit `encounter_key` and no `patient_key`; they were completed before
`validate-demo` enforced `missing-resource-key`. A byte-identical replay would
have been rejected at the demo gate *after* the reopen was spent — and
`milrinone` gates `vasoactive_agent`, so it would have stalled a wave-1 concept
too. They need a session that adds the key and leaves the logic alone, so they
are a reopen, not a replay. Run them **before** the replay pool.

## Run it

Everything below is wrapped by `./mimic-iv/concepts_fhir/rerun_fixed_build.sh`,
which holds the reason strings, sets `MIMIC_SPARK_LOCK`, runs the preflight over
the whole list before opening anything, and drops the relint concepts out loud:

```bash
cd mimic-iv/concepts_fhir

./rerun_fixed_build.sh --check-only     # preflight only; nothing is opened
./rerun_fixed_build.sh --relint         # the 2 that need patient_key, first
./rerun_fixed_build.sh -k 6 --dry-run   # the 47 replays, previewed
./rerun_fixed_build.sh -k 6             # ... and run
./rerun_fixed_build.sh --reimplement    # the 3, after their section-5 reopens
```

`--wave N` scopes any of it to one wave; `-- <args>` passes anything else
straight to `goal-run`. The rest of this section is what the script does, for
when you want to run a piece of it by hand.

### 0. Preflight — costs nothing, catches everything

```bash
export MIMIC_SPARK_LOCK="$HOME/.mimic-spark.lock"   # one local Spark at a time

# every refusal found here is free; the same refusal found after `replay` has
# already spent the reopen is not
for c in $(cat mimic-iv/concepts_fhir/replay/wave0.txt); do uv run mimic_utils replay "$c" --check; done

uv run mimic_utils replay-run $(cat mimic-iv/concepts_fhir/replay/wave0.txt) \
    --reason "upstream #124/#126 fixed, warehouse rebuilt 2026-08-24" \
    --wave 0 --dry-run
```

`--check` exits 5 on a refusal. As of 2026-08-24 the whole 49-concept list
returns **47 replayable, 2 refused** (`milrinone`, `creatinine_baseline`, both
`missing-resource-key` — see "Four routes"), plus warnings on `dobutamine`,
`milrinone`, `norepinephrine`, `phenylephrine`, `vasopressin` (part of their
divergence is `linkorderid`, still open) and on any concept whose declaration
prose cites a repaired mechanism. A warning is not a refusal; it says the
outcome will be `review` again on that part, which is correct.

### 1. Wave 0 — 30 concepts, no in-scope dependencies

```
acei antibiotic arb bg blood_differential cardiac_marker chemistry coagulation
complete_blood_count crrt dobutamine enzyme height icp icustay_detail
icustay_times inflammation invasive_line kdigo_creatinine milrinone
norepinephrine nsaid oxygen_delivery phenylephrine rhythm rrt urine_output
vasopressin vitalsign weight_durations
```

```bash
uv run mimic_utils replay-run $(cat mimic-iv/concepts_fhir/replay/wave0.txt) \
    --reason "upstream #124/#126 fixed, warehouse rebuilt 2026-08-24" \
    --wave 0
```

Per concept: `replay` → `validate-demo` → `run-demo` → `validate-full` →
`hpc-launch`; the whole wave is queued before any polling; then `hpc-poll` each
and promote every `match` to `COMPLETED`. Progress is flushed to
`replay/0.json` after every stage, so an interruption resumes — and a concept
whose ledger says it launched is never launched twice (`hpc_job.json` is
write-once; a second launch abandons a live job and spends one of the ten runs).

To finish a wave that was launched earlier:

```bash
uv run mimic_utils replay-run $(cat mimic-iv/concepts_fhir/replay/wave0.txt) --reason "..." --wave 0 \
    --stages poll promote
```

### 2. Judge the ones that come back `review`

The driver prints them as `/goal <concept>` lines. Run each in its own fresh
OpenCode session, as usual. `resume` will print a **REPLAY (data rebuild)**
block instead of the usual REOPENED block — it says the port was carried
forward and that no stage may author SQL. Phase 3 does not run; the session
exists for the judge.

Six concepts in wave 0 **cannot** reach `match` and will always need this,
because they declare a column unrepresentable and it is therefore 100% NULL by
design: `dobutamine`, `icustay_detail`, `milrinone`, `norepinephrine`,
`phenylephrine`, `vasopressin`.

### 2b. Or drive the sessions themselves — `goal-run`

`replay-run` stops where a model is needed. `mimic_utils goal-run` goes the rest
of the way: it reopens each concept, starts a real
`opencode run --agent concept-port-orchestrator --auto` session on it, keeps
sending that session a continuation until it emits a terminal `[goal:...]`
marker, and runs **k of them at once** — as one finishes, the next eligible
concept starts.

The `--reason` is not just an audit string: `replay` records it and `mimic_utils
resume` prints it back inside the REPLAY block, which is how the session learns
what changed. It is the only channel — `/goal` takes the bare concept stem and
rejects prose beside it — so write it for the agent.

```bash
export MIMIC_SPARK_LOCK="$HOME/.mimic-spark.lock"

REASON="The MIMIC-on-FHIR warehouse was rebuilt on 2026-08-24 after two upstream data defects were fixed: FHIR resources are now generated under UTC, so wall-clock timestamps are no longer shifted an hour across the spring-forward boundary, and Patient.birthDate is now derived from the anchor year and age rather than from the first transfer. This port was carried forward byte-identical to re-measure it against the corrected data -- do not re-author it. Expect previously accepted divergences to have shrunk or gone; if an hour-wide shift still appears, treat it as a finding and establish why the correction did not reach that path rather than accepting it as an upstream artifact."

uv run mimic_utils goal-run --wave 0 -k 6 --reason "$REASON" --dry-run
uv run mimic_utils goal-run --wave 0 -k 6 --reason "$REASON"
```

It deliberately does **not** mention the third fix (chartevents text in
`Observation.component`). No replayed concept may act on it, and naming a newly
served element to a session forbidden from re-authoring is an invitation to try.
It belongs only in the three re-implement reasons in §5.

Which of the two to use:

| | `replay-run` | `goal-run` |
|---|---|---|
| model cost | none | a full orchestrator session per concept |
| `match` | promoted automatically | promoted by the session |
| `review` | printed as a `/goal` line to run by hand | judged in the same session |
| writes `metrics/<concept>/run_NNNN.json` | no (no session to aggregate) | yes |

So `replay-run` first is still the cheaper order for a wave you expect to be
mostly `match`; `goal-run` is the one to reach for when most of the wave will
need a judge anyway (wave 0's six declaration concepts, or the re-implements),
or when you simply do not want to babysit terminals.

**The waves are a `replay-run` constraint, not a `goal-run` one.** `replay-run`
has a real barrier — it queues an entire wave to the cluster before polling any
of it — so a wave has to be a set that can all be in flight at once.
`goal-run` gates each concept on its own dependencies and has no barrier, so
feeding it one wave at a time makes `charlson` wait for all 30 of wave 0 when it
only needs `icustay_detail`. Hand it the lot instead:

```bash
uv run mimic_utils goal-run $(cat mimic-iv/concepts_fhir/replay/wave*.txt) -k 6 \
    --reason "$REASON"
```

That is all 49 replays — 30 + 15 + 4 — in one pool, with the ledger at
`all.goalrun/ledger.json`. Use `--wave N` when you want a wave's worth of
work bounded and reviewable before committing to the next; use the combined form
when you want the pool saturated.

Ordering is enforced, and the enforcement is not the obvious one: the gate asks
whether a dependency has finished **in this pool**, not whether it is
`COMPLETED` on disk. Every concept in a replay wave is `COMPLETED` when the wave
starts — that is what makes it replayable — so a disk check passes for all of
them at once and a dependent would open before its dependency had been reopened,
then be measured against the dependency's *old* candidate. A dependency outside
the run set is left to `replay`/`start`, which already refuse it.

For the three re-implements, keep the tailored reopen reasons from §5 and run
the sessions with `--mode none`, which drives an already-open concept:

```bash
# after the reopen + carryover-invalidate calls in §5
uv run mimic_utils goal-run gcs first_day_gcs ventilator_setting -k 2 \
    --mode none --reason "upstream e7c326b (#125), chartevents value text"
```

`first_day_gcs` will wait for `gcs` on its own.

Resuming is by ledger: `<wave>.goalrun/ledger.json` is flushed on every turn, a
concept already terminal is skipped, and a concept with a recorded session id is
**continued, not restarted** — a restart would re-enter the loop on an
already-open concept and spend a second HPC run. Session transcripts land in
`<wave>.goalrun/sessions/<concept>.jsonl`; each worker's goal-plugin state is
isolated under `<wave>.goalrun/goalstate/<concept>/`, because that plugin holds
an exclusive lease and would otherwise refuse workers 2..k and fight with your
own `.opencode/goals/state.json`.

Pick `k` from the local Spark, not the cluster: every worker's `run-demo` takes
the `MIMIC_SPARK_LOCK` flock in turn, so beyond about 6 the extra workers spend
their time queueing for it. HPC launches genuinely do run in parallel.

### 3. Wave 1 — 15 concepts (after wave 0 is fully terminal)

```
charlson creatinine_baseline first_day_bg first_day_bg_art first_day_height
first_day_lab first_day_rrt first_day_urine_output first_day_vitalsign
first_day_weight icustay_hourly kdigo_uo suspicion_of_infection
urine_output_rate vasoactive_agent
```

The order is **forced, not a convenience**: `replay` and `start` both check
`_missing_dependencies`, so a dependent cannot open while its dependency is
mid-replay. `replay --check` says so explicitly rather than failing obscurely.

Five of these (`first_day_bg_art`, `first_day_height`, `first_day_lab`,
`first_day_rrt`, `first_day_weight`) currently hold an **exact** `match` and are
in scope anyway: both runners preprocess a dependency's own attempt output, so
when a dependency's values change, so does the dependent's candidate — its
verdict was earned against the old ones. They are cheap: a replay returning
`match` is promoted with no session at all.

### 4. Wave 2 — 4 concepts

```
kdigo_stages meld norepinephrine_equivalent_dose sirs
```

### 5. The three that need re-implementing

Not replayable, and `replay` refuses them by name. `gcs` and `first_day_gcs`
both declare `gcs_unable` unrepresentable "because the No Response-ETT
discriminator is discarded", and upstream now serves exactly that
discriminator — a byte-identical replay would emit the same NULLs, satisfy its
own declaration (the column really is 100% NULL), and be accepted a second
time. `ventilator_setting` is blocked on 652,532 NULL rows in
`ventilator_mode` / `_hamilton` / `ventilator_type` for the same reason.

```bash
# gcs first (first_day_gcs depends on it)
uv run mimic_utils reopen gcs --by human --reason \
  "Upstream e7c326b (#125) now carries chartevents.value in \
Observation.component[].valueString, coded with the same mimic-chartevents-d-items \
coding as Observation.code. itemid 223900 therefore distinguishes 'No Response' \
from 'No Response-ETT' again. The unrepresentability declaration for gcs_unable \
is now FALSE and must be removed: select the component text and derive gcs_unable \
from it, and drop the ambiguity-propagation logic that emitted NULL for gcs, \
gcs_motor, gcs_verbal and gcs_eyes on affected windows. Do not reconstruct any \
resource id."
uv run mimic_utils carryover-invalidate gcs --stage fhir-prober --reason \
  "chartevents value text is now served in Observation.component; the mapping \
this stage recorded predates the element."
# then, in a fresh session:  /goal gcs

# same shape for ventilator_setting (223849 / 223848 / 229314 mode+type text)
# and then first_day_gcs, once gcs is terminal.
```

`ventilator_setting` is `BLOCKED_REPRESENTATION`, which `reopen` accepts
(`REOPENABLE_STATUSES`), so no state surgery is needed.

The component is emitted **only** where the source text is not the number
restated (`fhir_observation_chartevents.sql:97-113`), so treat it as
`forEachOrNull` and expect it on a minority of rows. It has not yet been probed
against the rebuilt warehouse — that is the prober's first job, and the count
belongs in `MIMIC_NOTES.d/<concept>.md`.

### 6. Leave alone, and say why in the results table

| concept | why | what a rerun would change |
|---|---|---|
| `code_status` | blocked on the absent hospital `poe`/`poe_detail` branch — 197,931 of 269,072 rows | its 4 residual DST rows clear; the block stands |
| `dopamine`, `epinephrine` | `linkorderid` still unserved | nothing |
| `neuroblock` | `orderid` still unserved | nothing |

## Gotchas

- **A refusal costs nothing; a spent reopen does not come back.** Run
  `replay --check` over a whole wave before running anything.
- **Never touch a concept another terminal holds.** `replay` refuses a live
  concept exactly as `resume --apply` and `retry` do. `--force` is for a session
  you *know* is dead.
- **The run cap is per concept and counts from the reopen baseline.** Worst case
  here is `crrt` at `hpc_counter=7`; a replay spends one run.
- **`review` is not a regression.** For the five `linkorderid` concepts and the
  six with declarations it is the correct outcome. Read the tier: a
  `contested`/`attributed` result citing the DST cast after this rebuild *is* a
  finding — it means the fix did not reach that path, and it should be
  investigated rather than accepted.
- **One local Spark at a time.** The driver runs `run-demo` sequentially and
  each takes the `flock`; set `MIMIC_SPARK_LOCK` so a hand-run `/goal` in
  another terminal queues rather than collides. `goal-run` sets it in every
  worker for the same reason, and respects it if you have already exported one.
- **`goal-run` and concurrent git commits.** Each session makes its own
  success-only `git commit --only <pathspecs>` at the end. `--only` means the
  commits do not overlap in content, but they do contend on `.git/index.lock`,
  so with a large `k` an occasional commit can fail. It is loud and the session
  retries; it is not silent corruption. Worth knowing before reading a stray
  "Unable to create index.lock" as something worse.
- **`goal-run` continues, it does not supervise.** A session that stalls without
  emitting a marker is stopped by `--max-turns` (30) or `--concept-budget`
  (6 h) and reported as `exhausted`/`timeout` with its session id, for you to
  reattach to. The ledger's per-turn record is the place to look first.

## Still to decide

- ~~`LOOP_CONTRACT.md` has not been revised.~~ **Done 2026-08-24.** The DST
  exemption is now *conditional* rather than withdrawn: an `attributed` shift is
  still acceptable, but only once the judge has established **why it is there**
  — a build predating the fix, or a path the fix did not reach. Neither, and it
  is `bug`, because a port defect one hour wide replays identically. Revised in
  `LOOP_CONTRACT.md` ("The DST cast is fixed; the exemption is now
  conditional"), `equivalence-judge.md`, `mismatch-diagnostician.md`, both
  skills, and — because prose is not a control — in the comparator itself:
  `divergence.diagnostician_required` is now `true` on `attributed`, and
  `divergence.judge_bar` states the three-way question in the artifact the judge
  actually reads. Expect this tier to stop firing entirely if the fix holds; if
  it fires, that is the signal worth spending a diagnosis on.
- **Metrics.** `metrics-finalize` aggregates an OpenCode session, and a
  `replay-run` replay has none, so no `metrics/<concept>/run_NNNN.json` is
  written for it. The previous run's artifact stands and the replay's real cost
  is HPC time (`hpc_accounting.json`) plus the wave ledger. Decide whether the
  results table needs a metrics artifact for these runs before the wave, not
  after — **and note this is now a choice of driver, not a constraint**:
  `goal-run` runs a real session per concept, so it writes the artifact.
  Metrics-completeness is a reason to prefer it even where `replay-run` would
  have been cheaper.
- **`icustay_hourly` and `urine_output_rate`** use `DATE_FORMAT` / sub-day
  `DATE_TRUNC`, which `TODO_warehouse_rebuild.md` established are harmless only
  while the Spark session zone is pinned to UTC. The pin is in
  `submit_concept_run.slurm` and `embedded_runner.py`; both replays inherit it.
  No action, just do not remove the pin.
