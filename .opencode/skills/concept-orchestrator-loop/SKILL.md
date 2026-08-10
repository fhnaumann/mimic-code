---
name: concept-orchestrator-loop
description: Drive the MIMIC-IV to MIMIC-on-FHIR concept port loop — receive one named concept, validate against the DAG via mimic_utils init/start, schedule subagents sequentially (source-analyst → fhir-prober → concept-implementer → demo-runner → hpc-launcher/poller → mismatch-diagnostician → equivalence-judge). Demo is a cheap shape gate only; full-data HPC comparison decides correctness, capped at 10 runs per concept. Trigger phrases include "port concept", "convert concept", "migrate concept to FHIR", and the /goal command.
---

# concept-orchestrator-loop

The primary loop for the MIMIC-IV → MIMIC-on-FHIR concept port. This skill
is loaded by `concept-port-orchestrator` and is authoritative for the loop,
subagent topology, wait mechanism, terminal-state markers, and CLI usage.

**On gate semantics, `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` outranks this
file.** Read it first. In short: demo is a cheap shape gate that can only
reject malformed ports (0 rows ⇒ `unsure`, never `fail`); full data on HPC is
the real correctness signal and runs as many times as needed, capped at 10.
Row count is **not** a hard gate on either leg, and neither is a value
conflict — the full comparator classifies divergence and returns `match` /
`mismatch` / `review`, and the judge decides every `review`.

`mismatch` is narrow: the candidate did not execute, the schema is wrong, or a
declaration the data refutes. Everything else that diverged is `review`,
carrying `divergence.tier` — `gap_shaped` or `contested`. **Expect most
concepts to land in one of those two.** Not one table maps cleanly; a loop that
treats divergence as failure will terminate almost every concept short of the
judge, which is the failure mode this contract was revised to remove.

`mimic-iv/concepts_fhir/MIMIC_NOTES.md` carries the dataset/IG quirks
accumulated across concepts, and `MIMIC_NOTES.d/<concept>.md` is where this
loop writes its own. Read both at intake — see "Shared dataset knowledge"
below.

## CLI orchestration (ConversionController)

The orchestrator MUST use the `ConversionController` CLI
(`src/mimic_utils/conversion_state.py` + `conversion_cli.py`), never
ad-hoc directory creation. Run commands as `uv run mimic_utils ...`; the
shorter `mimic_utils ...` spelling below names the subcommand only.

1. **`mimic_utils init <concept>`** — validates DAG membership, derives
   category from DAG node path, creates PENDING state at
   `mimic-iv/concepts_fhir/state/<concept>/state.json`.
2. **`mimic_utils depcheck <concept>`** — verify all `mimiciv_derived`
   dependencies are COMPLETED before starting.
3. **`mimic_utils start <concept>`** — creates the immutable attempt directory
   at `mimic-iv/concepts_fhir/concepts/<category>/<concept>/attempt_NNNN/` and
   transitions to RUNNING. Returns the attempt path. It does **not** arbitrate
   concurrency: other concepts being active is expected, because the human
   composes waves of parallel goals.
4. **`mimic_utils validate-demo <concept>`** — freezes implementation
   artifacts and transitions to VALIDATING_DEMO before demo execution.
5. **`mimic_utils validate-full <concept>`** — transitions to VALIDATING_FULL
   before the full-MIMIC HPC execution.
6. **`mimic_utils done <concept>`** — transitions to COMPLETED. Legal **only**
   for a `match` verdict.
7. **`mimic_utils accept-divergence <concept> --justification "..."`** —
   transitions to COMPLETED_WITH_DIVERGENCE after a judge `accept` on a
   `review`. The justification is required and must carry the judge's citation.
   `--by human` records a manual override instead; that is **yours to run only
   when the user asks for it**, never on your own authority.
8. **`mimic_utils fail <concept> --error "..."`** — transitions to FAILED.
9. **`mimic_utils block <concept> --error "..."`** — records a representability
   blocker for human review. A block is not the end of the concept: a human can
   clear it with `accept-divergence --by human`, or send it back to RUNNING.
10. **`mimic_utils status`** — full DAG-wide status report. It prints exact
    matches, judge-accepted divergences and human overrides on **separate
    lines**; never sum them. It lists every active concept, so under a wave it
    will show siblings you are not porting. That is normal — act on your own
    concept only, and never transition another goal's.
11. **`mimic_utils resume <concept> [--apply]`** — says which phase to
    re-enter and which transitions must happen first. See Phase 1.
12. **`mimic_utils carryover <concept>`**,
    **`carryover-record <concept> --stage S`**,
    **`carryover-invalidate <concept> --stage S --reason "..."`** — which
    analysis stages can be reused on the next attempt. See Phase 3.
13. **`conversion_metrics_finalize({concept: <concept>})`** — OpenCode tool,
    not a shell command. After any terminal conversion outcome, deterministically
    aggregates the dedicated root session(s) and descendant subagents and writes
    `mimic-iv/concepts_fhir/metrics/<concept>/run_NNNN.json` once.

The controller uses three counters: `semantic`, `engineering`, `hpc`.
Lifecycle: `PENDING → RUNNING → VALIDATING_DEMO → VALIDATING_FULL →
COMPLETED | COMPLETED_WITH_DIVERGENCE` (with FAILED / SKIPPED terminal branches
and FAILED → RUNNING / SKIPPED → RUNNING retry paths).

A `COMPLETED_WITH_DIVERGENCE` dependency **satisfies** `depcheck`, but the
dependent concept inherits its gap. Before spawning the judge, call
`ConversionController.divergent_dependencies(<concept>)` and pass the list into
the judge's task text, so it can tell inherited divergence from this concept's
own.

## Loop phases

### Phase 0 — Concept intake
Receive exactly one named concept from the `/goal` argument. Never accept
multiple concepts. Never auto-advance to the next concept. Other goals porting
other concepts at the same time is expected and is none of your business.
The command is exactly `/goal <concept>` and starts in a fresh dedicated
OpenCode session. Never reuse a finalized conversion's root session for another
run or concept; doing so would contaminate its token total. A resume may start
in another fresh session, which the metrics plugin attaches to the unfinished
run.

Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md` now, before spawning anything, and
the fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/` with it. Together they
tell you which quirks the pipeline already knows about, so you can recognise a
subagent re-deriving one — and recognise a genuinely new finding worth
recording when the loop ends. The two are not equal evidence: `MIMIC_NOTES.md`
is curated, the fragments are other loops' unconfirmed hypotheses.

### Phase 1 — DAG validation, or resumption

**Run `mimic_utils resume <concept>` first, before `init`.** A concept may
already be part-way through — a previous session that was interrupted, or one
whose attempt failed the demo gate. `resume` reads the state and the newest
attempt's artifacts and prints the phase to re-enter, the transitions needed to
get there, and which analysis stages are reusable. It changes nothing without
`--apply`.

- `ERROR: ... has not been initialised` → this is a fresh concept. Run
  `mimic_utils init <concept>`, then continue to Phase 2.
- `action: nothing_to_do` → the port is finished. Report and stop.
- `action: blocked` → representability blocker awaiting a human. Report and stop.
- `action: start_new_attempt` → run `mimic_utils resume <concept> --apply`. It
  performs the `fail`/`start` transitions and prints the new attempt directory.
  **Skip Phase 2** — the attempt already exists — and enter at the phase named
  in the plan.
- `action: continue_attempt` → the existing attempt directory is still live.
  Skip Phase 2 and enter at the phase named in the plan. Any transition the plan
  lists (e.g. `validate-full`) is yours to run; `--apply` deliberately does not
  spend an HPC run for you.

On a `VALIDATING_FULL` concept the plan is determinate: it reads `hpc_job.json`
and tells you either **poll job `<id>`** (with the time it was submitted) or
**launch**. Follow it literally. Guessing "launch" on an attempt that already
has a job record hits *"hpc_job.json already exists"*, and obeying that error
abandons a live cluster job and spends one of the ten runs.

`resume --apply` and `retry` **refuse a concept that still looks live** — the
sign that another terminal is porting it right now. Report the refusal and
stop. Do **not** reach for `--force`: that flag is for a human who knows a
session is dead, and using it on an error you have not diagnosed is how one
goal destroys another's attempt.

`init` still validates DAG membership and category for a fresh concept, and
`mimic_utils depcheck <concept>` must report all dependencies COMPLETED before
starting. If it reports unmet dependencies, halt and report. Do not proceed.

Do **not** re-run `init` on a concept that has one: it errors with "already
initialised", which is a statement about state, not a failure to route around.

### Phase 2 — Create attempt (start)
Skip this phase entirely when Phase 1 resumed — the attempt directory exists.

Run `mimic_utils start <concept>`. This creates the immutable attempt
directory and records the path. Note: the controller increments the
attempt counter; the directory is `attempt_NNNN/` (zero-padded to 4 digits).

### Phase 3 — Sequential subagent pipeline

**Run `mimic_utils carryover <concept>` first, and skip every stage marked
`reuse`.** The two analysis stages produce concept-level facts — which source
columns matter, which codes the SQL names, which FHIR element carries them —
and those do not change between attempts. A retry that re-runs them pays two
agent runs to regenerate a file it already has. When a stage is marked
`reuse`, read
`mimic-iv/concepts_fhir/carryover/<concept>/<stage>.md` and pass its contents to
the implementer exactly as if the agent had just produced it.

A stage marked `RERUN` is either absent or invalidated by a diagnosis. Spawn it.

Spawn the stages you did not skip, one at a time, each feeding off the previous:

1. **source-analyst** — reads `mimic-iv/concepts/<dag_node_path>.sql`, produces
   structured analysis.
2. **fhir-prober** — maps source tables/columns to FHIR resources/element
   paths using the MIMIC-on-FHIR IG and Pathling `$fhir` endpoint, and
   confirms the source SQL's literal code set against the served data. It reads
   `MIMIC_NOTES.md` plus the `MIMIC_NOTES.d/` fragments and appends its own
   findings to `MIMIC_NOTES.d/<concept>.md`.
3. **concept-implementer** — creates one or more
   `ViewDefinition.<label>.json` files and `concept.sql`
    once in the write-once `attempt_NNNN/` directory, using the proven
   ViewDefinition format (select.column `path`/`name`, `forEach`/`forEachOrNull`)
   from
   `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/`.
   The SQL selects from each ViewDefinition's label, which the runner binds as a
   Spark temp view — there is no registration step.

### Phase 4 — Demo shape gate (demo-runner)
Run `mimic_utils validate-demo <concept>` before execution, then spawn
`demo-runner`, which runs `mimic_utils run-demo <concept>` against the local
demo Delta warehouse.

**Both legs run Spark.** The demo gate uses embedded Pathling on Spark (the
default engine) because the full-data gate has no alternative — compute nodes
have no FHIR server. Keeping the engines identical is what makes a demo failure
predict a full-run failure; a demo that passed on a server could still fail on
Spark, and it would fail on the HPC, after a queue slot had been spent. There is
no server backend and no second engine — that is the point.

Both legs write Parquet, so the shape gate reads the Spark schema rather than
re-inferring types from text. Do not add a text intermediate anywhere between a
runner and the comparator: an all-null column infers as `JSON` and a `DECIMAL`
as `VARCHAR`, which fails the gate for reasons that are about the file format,
not the port.

This is a **cheap shape gate, not a correctness gate** — seconds, no queue. It
exists to catch, before an HPC run is spent:

- the ViewDefinition or SQL failing to execute at all
- column **names** that do not match the oracle
- column **types** that are incompatible
- structurally wrong output shape

Explicitly **not** demo gates:
- **Row count is not gated on demo.** Demo agreement is not evidence of
  correctness, and demo disagreement on count is not proof of a bug.
- **0 rows on demo is `unsure`, never `fail`.** Do not fail and do not pass —
  proceed to Phase 6.

Target shape comes from `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json`
(columns, types, key), so the demo gate needs no oracle export.

- **Shape gate passes or returns `unsure`** → go to Phase 6.
- **Shape gate fails** → go to Phase 5 (diagnose and retry). Do **not** spend
  an HPC run on a port that does not execute or has the wrong columns.

### Phase 5 — Mismatch resolution
1. **Spawn mismatch-diagnostician** — diagnoses root cause. On a full-data
   `mismatch` or a `contested` review it reads `divergence.unresolvable` /
   `divergence.contested` and `diff.columns_conflicting`, which name the
   offending class and column.
   Skip this step when you already hold a diagnosis — a resumed session whose
   plan named the failure, or a `shape.demo.json` whose `schema.hints` state the
   remedy outright. The diagnostician exists to produce a diagnosis, not to
   confirm one.

   It re-reads `MIMIC_NOTES.md` and `MIMIC_NOTES.d/*.md` here even though Phase
   0 already read them. This is the high-value re-read: it is the last look
   before a fix is authored, and it is the only stage guaranteed to run on the
   failure path, because `fhir-prober` is frequently skipped as `reuse` on a
   retry. Hours may have passed, and a sibling loop's fragment may name exactly
   this divergence.

2. **Invalidate the carryover stage the diagnosis blames**, if any:
   `mimic_utils carryover-invalidate <concept> --stage <stage> --reason "..."`.
   This is what keeps reuse safe. A diagnosis of "mapped the wrong resource"
   or "wrong coding system" indicts `fhir-prober`, and
   reusing that analysis on the next attempt reproduces the same failure — the
   loop would burn all ten attempts converging on nothing. A diagnosis that
   blames only the SQL or the ViewDefinition invalidates nothing: that is
   implementer output, which is attempt-scoped and never carried over.

3. If diagnosis says **fixable semantic bug** — a wrong filter, join,
   aggregation, mapping, or value meaning in a port that executed — run
   `mimic_utils fail <concept> --counter semantic --error "..."`. This explicit
   counter is the metric's semantic-rework signal. Invalid SQL/ViewDefinition,
   wrong shape, environment, transfer, queue and tool failures are not semantic
   rework; use the default engineering counter for those. Then run
   `mimic_utils retry <concept>` to create a new write-once attempt
   (or, after that explicit `fail`, `mimic_utils resume <concept> --apply`). The
   implementer reads the previous attempt, creates corrected artifacts
   once in the new directory, and loops back to Phase 4.
4. A `mismatch` is **never** routed to the judge — it means the result is not
   comparable or the port contradicted itself, so there is nothing to weigh.
   A `contested` **`review`** is a different thing and DOES reach Phase 7.

**A conflict is not automatically a bug.** `differing_conflict` and
`only_candidate` used to hard-fail here. They no longer do, because
MIMIC-on-FHIR rewrites values as well as omitting them — `fhir_patient.sql:15`
synthesises `birthDate` from `MIN(transfers.intime)`, `fhir_encounter.sql:65`
DST-shifts admission times — and no port can invert either. The diagnostician's
job on a `contested` result is to decide **which** it is:

- **the port is wrong** (fan-out, a filter, a missing CAST, a mapping the notes
  already record a workaround for) → fix and retry, exactly as before;
- **upstream ETL transformation loss**, cited to a `mimic-fhir/sql/*.sql` file
  and line, with the oracle value unrecoverable by any query → say so, and
  route to **Phase 7**. Do not retry; there is nothing to fix.

If the diagnostician cannot cite the ETL statement, it is a bug. "No obvious
fix" is not a citation, and neither is "this looks intrinsic".

A conflict still outranks a gap: a result carrying both is `contested`, and the
gap remaining after a genuine fix is often smaller than it first appeared.

### Phase 6 — Full-data correctness (the real gate)
Run `mimic_utils validate-full <concept>`, then spawn `hpc-launcher`
(`mimic_utils hpc-launch <concept>`) and `hpc-poller`
(`mimic_utils hpc-poll <concept>`) sequentially. Require a fresh
`comparison.full.json` — **queue exit alone is not success**, because a job
that OOMs also leaves the queue. Distinguish the poller's *outcome*
(`complete` / `crash` / `timeout`) from the *verdict* inside the fetched
comparison (`match` / `mismatch`); a `mismatch` is a real verdict and routes to
Phase 5, a `crash` is not a verdict at all.

The job runs embedded Pathling on the compute node — no FHIR server is involved
on full data. See `.opencode/skills/hpc-transfer/SKILL.md`.

The oracle is **already computed**: never recompute the derived concept. The
job compares the candidate against the read-only full oracle at
`/scratch3/nau025/oracle/mimic4-full.db`, node-local beside the FHIR
warehouse.

- **Column schema identity** — hard gate.
- **Keyed row-level diff** — full outer join on the manifest key, then
  per-column comparison; full-tuple multiset for the 13 unkeyed concepts.
- **Row count** — reported, **never gated**. FHIR does not carry everything
  relational MIMIC-IV carries.

This is **not** a one-shot confirmation of a demo-approved answer. The agent
may submit **as many full runs as it judges necessary**, iterating on the diff
each time.

Route on the comparator's verdict, never on the row-count delta:

- **`match`** → run `mimic_utils done <concept>` and go to Phase 8. Do **not**
  spawn the judge.
- **`mismatch`** → go to Phase 5. The result is not comparable or the port
  contradicted itself; the judge cannot help.
- **`review`, tier `gap_shaped`** → go to Phase 7.
- **`review`, tier `contested`** → go to Phase 5 for a diagnosis **first**, then
  Phase 7 if and only if the diagnostician cites the upstream ETL statement.
  This is the one route that visits Phase 5 without necessarily retrying.
- **10 full runs reached without convergence** → hard cap. Run
  `mimic_utils fail <concept> --error "full-run cap reached"` and terminate
  with `[goal:blocked]` for human review.

### Phase 7 — Equivalence judge
Spawn `equivalence-judge` for a **`review`** verdict, and only for that. Never
for a `match`; never to reconsider a `mismatch`.

Pass it: the concept name, attempt number, `comparison.full.json`, the tier and
`divergence.judge_bar` from that file, the full attempt history, the
diagnostician's findings, and the output of `divergent_dependencies(<concept>)`
so it can separate inherited divergence from this concept's own.

On a `contested` tier, the diagnostician's ETL citation is the centre of the
case — pass it verbatim, including the file and line. A `contested` review with
no diagnosis attached should not be sent to the judge at all; go to Phase 5.

Do **not** retry blindly and do **not** mark a `review` failed: `hpc-poll` exits
**2** here, not 1, and a caller that reads any non-zero exit as failure will get
this wrong. That misreading is most likely on `contested`, which reads as
serious.

- `accept` → gap is intrinsic and the port is as faithful as the data allows.
  Write the exception once, run
  `mimic_utils accept-divergence <concept> --justification "<the judge's cited
  reason>"`, and continue to Phase 8's divergence terminal sequence.
- `bug` → judge says the divergence is fixable. Loop back to Phase 5.
- `blocked` → intrinsic *and* severe enough that the result is not a port of
  the concept. Run `mimic_utils block <concept> --error "..."` and terminate
  with `[goal:blocked]`. Record the fidelity figures in the error message —
  a human clearing this block needs to know how much of the table was
  reproduced, and `representable_fraction` is the number that says so.

**You never run `accept-divergence --by human` yourself.** A manual override is
the user's decision about your loop's output; taking it on your own authority
would make the `judge` / `human` distinction meaningless in the one direction
that matters.

### Phase 8 — Terminal state
After the state transition to COMPLETED, COMPLETED_WITH_DIVERGENCE, FAILED, or
BLOCKED_REPRESENTATION, call `conversion_metrics_finalize` with the concept.
Do not infer or write metric values in prose: the tool reads OpenCode SQLite,
controller state and immutable attempt artifacts. Do not emit a terminal marker
until it reports the write-once metrics path. Finalization happens before this
last response, so the artifact records that the small terminal response itself
is excluded.

Emit terminal markers:
- On a full-data `match`, end with adjacent lines
  `[goal:evidence] <verified summary>` then `[goal:complete]`. A demo pass never
  justifies this sequence.
- On a judge `accept`, emit `[goal:complete-with-divergence]`, then end with
  adjacent lines `[goal:evidence] <summary explicitly naming
  COMPLETED_WITH_DIVERGENCE>` and `[goal:complete]`. The last marker terminates
  the goal extension; it is not an exact-match claim. The controller state and
  metrics artifact remain the research outcome.
- `[goal:blocked]` on a judge `blocked`, or on reaching the 10-run cap.
- Include a final evidence block summarizing: concept, attempt number, number
  of full runs consumed, verdict, the divergence classes and counts if any, the
  judge's citation if one was needed, artifact paths, and every entry this
  concept appended to `MIMIC_NOTES.d/<concept>.md` (or "none"), so the human
  merging between waves knows what is waiting. Include the metrics artifact
  path too.

## Attempt management (immutable, controller-driven)

- Each attempt is `mimic-iv/concepts_fhir/concepts/<category>/<concept>/attempt_NNNN/`.
- Each artifact is created once and never edited or replaced. Artifacts may
  be added while RUNNING; implementation artifacts freeze before
  `validate-demo`.
- A fix always requires `mimic_utils fail` followed by `mimic_utils retry`,
  creating a new attempt directory with an incremented counter.
- Only the orchestrator may promote a converged attempt to canonical.

## Evidence logging

After each subagent completes, create one evidence file at
`attempt_NNNN/evidence/<stage>.md`. Never append to or rewrite a file.

## Shared dataset knowledge: `MIMIC_NOTES.md` and the fragments

`mimic-iv/concepts_fhir/MIMIC_NOTES.md` holds the quirks of the MIMIC-on-FHIR
data and IG that are true regardless of concept — polymorphic fields needing
both variants COALESCEd, datetimes needing an explicit parse format, code
systems that are proprietary and flat, elements that are never populated. It
exists so the loop does not pay an HPC run to rediscover the same thing on the
next concept.

**It is read-only for a running loop.** Findings go to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/<concept>.md`, an append-only fragment
your goal owns outright, so a wave of parallel loops never contends over one
markdown file. A human merges the fragments into `MIMIC_NOTES.md` between
waves; that is also why an entry there means "checked" while a fragment means
"one loop currently believes". Protocol in `MIMIC_NOTES.d/README.md`.

`mimic-iv/concepts_fhir/carryover/<concept>/` (Phase 3) is unchanged: still
exempt from the write-once rule, still edited in place, still per-concept.

The three differ in scope, and mixing them up fills one with another's content:
`MIMIC_NOTES.md` and the fragments hold what is true of the **dataset**
regardless of concept; carryover holds what is true of **one concept**
regardless of attempt.

Who touches what:

| Agent | Reads | Writes `MIMIC_NOTES.d/<concept>.md` |
|---|---|---|
| `fhir-prober` | both, before mapping | yes — the primary discoverer, it is the agent looking at served data |
| `concept-implementer` | both, before authoring SQL | yes — constructs that fail over this warehouse |
| `mismatch-diagnostician` | both, before diagnosing | yes — a full-data divergence is the strongest evidence a quirk exists |
| `equivalence-judge` | `MIMIC_NOTES.md` **only** — fragments are provisional and its bar is evidence | **no** — verdict-only, changes no files |
| `demo-runner`, `hpc-launcher`, `hpc-poller` | not required | no |

Your job across the loop:

1. **At intake (Phase 0)** — read both, so you can tell a re-derivation from a
   discovery, and so you know which fragments are unverified.
2. **After each subagent (Phase 3 onward)** — its evidence block names what it
   read and what it appended. If it reports a dataset-wide quirk that is not yet
   recorded, append it to `MIMIC_NOTES.d/<concept>.md` yourself, in the file's
   format (`##` claim heading, `- Affected: <resource>.<field>`, `- Verified:`
   naming the concept, attempt number, and what was actually observed). Never
   edit `MIMIC_NOTES.md`, never touch another concept's fragment, and never
   rewrite a section already in your own.
3. **After the judge (Phase 7)** — the judge cannot write. If its rationale names
   an unrecorded quirk, append that entry before emitting the terminal marker.
4. **At terminal state (Phase 8)** — list in the final evidence block every
   entry this concept appended, or say plainly that it appended none. That list
   is what the human merges from.

The test is **generality, not size**: "this concept's filter was too narrow" is
concept-specific and stays in the evidence file; "this FHIR element is never
populated in the served warehouse" is dataset-wide and belongs in the fragment.

The file was seeded from
`../master_thesis_pipeline/paper_reproductions/MIMIC_NOTES.md`; the two have
diverged and are **not** synced automatically. Most existing `Verified:` lines
cite paths in that repo — treat them as provenance, and cite paths in *this*
repo for anything you add.

## External service dependencies

- **Spark + embedded Pathling** — the execution path for **both** legs of the
  loop: `run-demo` over the demo Delta warehouse locally, and `run-full` over
  the 156 GB warehouse on the HPC. This is the only path the loop should use.
  There is no HTTP Pathling server anywhere in the loop and no `preflight-fhir`
  command; both were removed because the server served different data from the
  warehouse, which made every check against it a statement about the wrong
  dataset. ViewDefinition authoring conventions still come from the
  `pathling-sql` skill even though the loop executes them through Spark.
- **No terminology service.** The loop resolves no codes at runtime. A concept's
  code set is the literal one its source SQL filters on, lifted verbatim by
  `source-analyst` and confirmed against the served data by `fhir-prober`. The
  FHIR side stores the same values (`Observation.code.coding.code` is a verbatim
  `CAST(itemid AS TEXT)`), so `CAST(code AS INTEGER)` is the whole mapping and
  there is nothing to translate. The HPC leg has no internet anyway.
- **Code-search** — `http://localhost:3000` for discovering codes from
  clinical text (secondary; primarily for paper reproductions).
- **HPC (Petrichor)** — for full-MIMIC execution, via `mimic_utils hpc-launch`
  and `hpc-poll`. Conventions are in this repo's own `hpc-transfer` and
  `csiro-hpc` skills; never follow a `../master_thesis_pipeline/...` path for
  cluster details. There is no HPC preflight command — SSH, the remote env and
  the warehouse are confirmed once by hand, and every launch runs a login-node
  smoke test that refuses to `sbatch` on failure.
