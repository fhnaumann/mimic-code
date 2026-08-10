# AGENTS.md — MIMIC-IV → MIMIC-on-FHIR concept port

This repo holds the canonical MIMIC-code concept library. The active task is a
port of MIMIC-IV concepts (SQL views over raw `mimiciv_hosp` / `mimiciv_icu`
tables) into MIMIC-on-FHIR representations (FHIR ViewDefinitions +
Pathling-derived SQL), run **one concept per `/goal`** — several goals may run
at once as a wave the human composes, but no goal ever takes two concepts or
advances to the next on its own.

Read this once. The orchestrator, subagents, and skills referred to here are
defined under `.opencode/` and are loaded automatically. External reference
repos — `../master_thesis_pipeline/orchestration-new` and
`../master_thesis_pipeline/paper_reproductions` — provide proven patterns and
pipeline infrastructure; consult them for conventions, but do not copy
destructive behaviours (e.g. `git checkout --` without preserving state) or
prompt-only state patterns.

---

## Repo overview

```
mimic-iv/
  concepts/                       # canonical concept SQL (source of truth)
    <category>/<name>.sql
  concept_dag/
    concept_dag.json               # machine-readable DAG of concept dependencies
    concept_dag.md                 # human-readable DAG reference (generated; hand edits are wiped)
  buildmimic/                      # dialect-specific build scripts (postgres, duckdb, …)
  concepts_fhir/                   # FHIR port output directory
    concepts/<category>/<concept>/ # per-concept port dir
      attempt_NNNN/                # immutable attempt subdirectories
    state/<concept>/state.json     # ConversionController state
    MIMIC_NOTES.md                 # shared dataset/IG quirks (curated, see below)
    MIMIC_NOTES.d/<concept>.md     # append-only per-concept findings fragment
src/mimic_utils/                   # Python: conversion state machine, DAG generator, transpile, compare
  conversion_state.py              # ConversionController — init/start/transition/depcheck
  conversion_cli.py                # CLI: init, start, validate-demo, validate-full, done, fail, skip
  concept_dag.py                   # DAG generator/validator
  db_preflight.py                  # Demo DB connectivity preflight
  __main__.py                      # mimic_utils CLI entrypoint
tests/                             # pytest suite
```

The DAG encodes build order: every concept lists its `mimiciv_derived`
dependencies and a full SHA256 of its current SQL source (64 hex chars).
Concept ports must preserve this dependency order — a concept cannot be
ported before every concept it references is also ported. The DAG structure
lives in `concept_dag.json` under keys `nodes` (dict of stems to {stem, path,
sha256, level, dependencies, dependents}), `edges` (list of {consumer,
dependency}), `topological_order`, and `levels`.

---

## Concept port workflow (per /goal)

1. **Orchestrator** receives the concept name, runs `mimic_utils init <concept>`,
   validates it against the DAG via the `ConversionController`, and schedules
   subagents sequentially.
2. **Source analyst** reads the concept's SQL, identifies referenced tables,
   columns, filters, joins, and any `mimiciv_derived` dependencies.
3. **FHIR prober** queries the MIMIC-on-FHIR IG (Pathling `$fhir` endpoint,
   local FHIR JSON snapshots) to map source columns to FHIR paths and
   element definitions.
4. **Implementer** authors the FHIR ViewDefinition and derived SQL.
5. **Demo runner** (`mimic_utils run-demo <concept>`) executes the
   ViewDefinition + SQL over the local demo Delta warehouse. This is a
   **cheap shape gate, not a correctness gate**: it catches execution failure,
   wrong column names, and incompatible types. Row count is **not** a demo
   gate, and **0 demo rows is `unsure`, never `fail`** — proceed to full data.
6. **Full runner** (`mimic_utils hpc-launch <concept>` then
   `mimic_utils hpc-poll <concept>`) executes the attempt on full data on the
   HPC and compares it against the immutable full oracle. This is where
   correctness is decided: schema identity and the classified keyed diff. Row
   count is reported, never gated. The
   agent may submit **as many full runs as it judges necessary**, up to a
   **hard cap of 10 per concept**.

   There is **no Pathling server in the full path**. Compute nodes have no
   internet, so the Slurm job embeds Pathling over PySpark
   (`mimic_utils.full_runner`), reads the Delta warehouse directly, and runs
   the keyed diff against the node-local oracle in the same process. Only two
   small JSON artifacts travel back.

   **Both legs run identical engine versions**, pinned in `pyproject.toml`'s
   `fhir` extra to exactly what Petrichor has: Python 3.12, pathling 9.6.0,
   pyspark 4.0.2, duckdb 1.5.5. Bump them only together with the remote env at
   `/scratch3/nau025/mimic-on-fhir-delta`. A local version that drifts ahead of
   the cluster costs the demo gate its entire reason to exist.

### Both legs run Spark

**Embedded Pathling on Spark is the execution path for the whole loop**, demo
and full alike, and it is the default for every command. The full leg has no
alternative, so making the demo leg match is what lets a demo failure predict a
full-run failure. Run the demo gate on an HTTP server instead and the Spark
path's first real execution happens on the HPC — where a failure costs a queue
slot rather than seconds, and where a passing demo told you nothing about it.

There is **no HTTP Pathling server in the loop**. It was removed rather than
kept as a fallback: it served different data from the Delta warehouse, so an
embedded-vs-server disagreement could never distinguish "Spark bug" from
"different dataset" — the one job a fallback was supposed to do. If you find
yourself wanting one, the answer is a smaller Delta warehouse, not a server.

Both legs write **Parquet** (`candidate.demo.parquet`, `candidate.full.parquet`),
and that is load-bearing rather than incidental. Parquet carries the Spark
schema; a text artifact does not, so a gate reading NDJSON checks DuckDB's
re-inference of serialised JSON instead of the types the run produced. An
all-null column — legitimate whenever a concept's shape requires a column
MIMIC-on-FHIR cannot populate — infers as `JSON` and fails a `SMALLINT`
expectation; a `DECIMAL` serialises to a string and fails a numeric one. Neither
is a port bug. Never reintroduce a text intermediate between a runner and the
comparator.

ViewDefinition *authoring* conventions are unaffected: the `pathling-sql` and
`fhir-mapping` skills still define how a ViewDefinition is written. Only the
execution engine is fixed to Spark.
7. **Mismatch diagnostician** (if mismatch) diagnoses root cause from the
   keyed diff. The implementer modifies only the ViewDefinition/SQL in a new
   immutable attempt; previous attempts are never rewritten. Then loop back
   to step 6.
8. **Equivalence judge** decides every `review` verdict — a result whose only
   remaining divergence is shaped like a MIMIC-on-FHIR coverage gap. It is
   **never called** for a `match`, and it **cannot override** a `mismatch`.
   Its verdict is either `accept` (the gap is intrinsic to the IG and the port
   is as faithful as the data allows → `COMPLETED_WITH_DIVERGENCE`) or `bug`
   (the divergence has a fixable cause → back to the diagnostician).
9. The concept completes when the full-data verdict is `match`, or when the
    judge accepts a `review`. A demo pass earns nothing except permission to
    spend an HPC run. Reaching 10 full runs without convergence terminates the
    concept for human review.

`mimic-iv/concepts_fhir/LOOP_CONTRACT.md` is the authoritative statement of
what is compared, where, and what gates what. If this file or any skill
disagrees with it, the contract wins and the other document is a bug.

---

## Shared dataset knowledge: `MIMIC_NOTES.md` and `MIMIC_NOTES.d/`

Quirks of the MIMIC-on-FHIR data and IG that hold regardless of which concept is
being ported live in `mimic-iv/concepts_fhir/MIMIC_NOTES.md`. It exists so the
same quirk is not re-derived, at HPC-run cost, once per concept. Protocol:

1. **Read it before probing the IG or authoring a ViewDefinition or SQL**, along
   with the fragments in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/`. The
   `fhir-prober`, `concept-implementer` and `mismatch-diagnostician` ground
   themselves in both; `equivalence-judge` reads `MIMIC_NOTES.md` only.
2. When you discover a **dataset/IG-level** quirk — true regardless of concept —
   append it to `MIMIC_NOTES.d/<concept>.md`, the fragment your goal owns.
   Concept-specific findings stay in that attempt's `evidence/<stage>.md`.
3. Each entry: short claim, affected resource/field, one line on how it was
   verified, so a later agent can trust-but-recheck cheaply.
4. Name the files in the evidence block whenever you read a quirk that changed
   your mapping, or wrote one — so the promotion is auditable from the attempt.

**`MIMIC_NOTES.md` is read-only for a running loop.** Several goals run at once
as a wave the human composes, and five loops editing one markdown file in place
lose each other's writes. Each writes to its own append-only fragment instead,
and a human merges them into `MIMIC_NOTES.md` between waves — which is also what
makes an entry there mean "checked" against a fragment's "one loop currently
believes". Treat another concept's fragment as a lead to verify, never as
evidence. Protocol in `MIMIC_NOTES.d/README.md`.

The judge is the exception in the other direction: it reads `MIMIC_NOTES.md` and
never writes, because it changes no files at all — a quirk it discovers goes in
its verdict prose for the orchestrator to record. Fragments are out of scope for
it deliberately: its bar promotes a notes entry to evidence, and a provisional
claim cannot carry that weight.

`carryover/` remains mutable and edited in place — see below. It was always
per-concept, so nothing about it changes here.

It was seeded from `../master_thesis_pipeline/paper_reproductions/MIMIC_NOTES.md`
and the two have since diverged; they are **not** synced automatically.

## Carryover — per-concept analysis reused across attempts

`mimic-iv/concepts_fhir/carryover/<concept>/<stage>.md` holds the output of the
two analysis stages (`source-analyst`, `fhir-prober`).
These are facts about **one concept** that do not change between attempts: which
source columns matter, which FHIR element carries them, which coding system an
itemid uses. A retry reads them instead of re-spawning the agent.

```
mimic_utils carryover <concept>                    # which stages are reusable
mimic_utils carryover-record <concept> --stage S   # after writing <stage>.md
mimic_utils carryover-invalidate <concept> --stage S --reason "..."
```

The rules that keep reuse honest:

- The stage agent writes its own `<stage>.md` and then records it. Overwriting
  is correct — the file always reflects the current best analysis.
- Reuse is revocable. A diagnosis that blames a stage invalidates it, and the
  next attempt re-runs it. Reusing a wrong analysis is how a loop spends all ten
  attempts converging on nothing.
- The implementer has no carryover. Its output *is* the attempt, and carrying it
  across attempts would defeat the write-once contract.
- "Not applicable" is a finding worth recording. A stage that determines a
  concept needs nothing from it still writes a one-line `<stage>.md`; an absent
  file re-spawns that agent on every future attempt.

Distinguish it from the notes: those hold what is true of the **dataset** across
concepts, carryover holds what is true of **one concept** across attempts. A
dataset-wide quirk found while probing belongs in `MIMIC_NOTES.d/<concept>.md`
even though you found it doing carryover work.

## Resuming an interrupted port

`mimic_utils resume <concept>` reads the state and the newest attempt's
artifacts and prints which loop phase to re-enter, which transitions are needed
first, and which carryover stages are reusable. It changes nothing until
`--apply`, which performs only the `fail`/`start` transitions — never a
full-data run, because nothing named `resume` should spend an HPC slot as a side
effect. At the HPC boundary it reads `hpc_job.json` and says *poll job `<id>`*
or *launch* rather than guessing: `hpc_job.json` is write-once, so a wrong guess
of "launch" abandons a live cluster job and burns one of the ten allotted runs.

`resume --apply` and `retry` **refuse a concept that still looks live** —
active, and stamped `updated_at` more recently than its staleness threshold.
Two terminals can hold the same concept name, and failing a live attempt to
open a new one throws away work in progress. `--force` overrides; the bar for
it is a session you *know* is dead, never an error you have not diagnosed.
`mimic_utils status` shows time since the last transition on every active
concept, and `--stale` lists just the ones past their threshold.

This exists because the state machine has no edge from `VALIDATING_DEMO` back to
`RUNNING`: rerunning a concept parked there without a `fail` first dies at
phase 2. Start every `/goal` with `resume`, not `init`.

Do not commit, push, or create PRs. Each attempt is immutable in its own
attempt subdirectory. State is managed by the `ConversionController` via
`mimic_utils init|start|validate-demo|validate-full|done|accept-divergence|fail|block`
CLI commands. In an unactivated shell, prefix every command with `uv run`, for
example `uv run mimic_utils status`.

---

## Artifact layout

State is managed by `ConversionController` (`src/mimic_utils/conversion_state.py`)
and its CLI (`mimic_utils init|start|validate-demo|...`). The canonical paths:

```
{repo_root}/mimic-iv/concepts_fhir/
  state/<concept>/state.json                    # ConversionController state
  concepts/<category>/<concept>/attempt_NNNN/   # immutable attempt dirs
  carryover/<concept>/<stage>.md                # mutable, reused across attempts
  carryover/<concept>/carryover.json            # freshness ledger
  MIMIC_NOTES.md                                # curated, read-only to a loop
  MIMIC_NOTES.d/<concept>.md                    # append-only findings fragment
```

- `category` is derived from the DAG node's `path` field (e.g. `medication/antibiotic.sql` → `medication`).
- Attempt directories are created by `mimic_utils start <concept>` and are
  write-once: an artifact may be added once during that attempt, but an
  existing artifact is never edited or replaced. A fix starts a new attempt.
- The controller uses three counters: `semantic`, `engineering`, `hpc`.
- The orchestrator calls:
  1. `mimic_utils init <concept>` — creates PENDING state
  2. `mimic_utils start <concept>` — transitions to RUNNING, creates `attempt_NNNN/`
  3. `mimic_utils validate-demo <concept>` — VALIDATING_DEMO
  4. `mimic_utils validate-full <concept>` — VALIDATING_FULL
  5. `mimic_utils done <concept>` — COMPLETED (verdict `match` only)
  6. `mimic_utils accept-divergence <concept> --justification "..."` —
     COMPLETED_WITH_DIVERGENCE, after a judge `accept` on a `review` verdict.
     Refuses without a justification.
  7. `mimic_utils fail <concept> --error "..."` — FAILED
  8. `mimic_utils block <concept> --error "..."` —
     BLOCKED_REPRESENTATION pending human review

Execution commands, distinct from the state transitions above:

| Command | Does |
|---|---|
| `run-demo <concept>` | demo shape gate — embedded Pathling on Spark over the demo Delta warehouse, writing Parquet |
| `run-full <concept>` | full-data execution + keyed diff — runs *on the HPC node*, invoked by the Slurm job, not by hand |
| `hpc-launch <concept>` | render `submit.slurm`, rsync, login-node smoke test, `sbatch`, record `hpc_job.json` |
| `hpc-poll <concept>` | poll `squeue` every 300 s, break on fatal markers, fetch the verdict |

Per-attempt artifacts: `ViewDefinition.<label>.json`, `concept.sql`,
`candidate.demo.parquet`, `shape.demo.json`, `submit.slurm`, `hpc_job.json`,
`candidate.full.parquet` (stays on scratch), `comparison.full.json`,
`run_meta.full.json`, `evidence/<stage>.md`. All write-once.

---

## External references

### `../master_thesis_pipeline/orchestration-new`

Provides the proven agentic pipeline architecture: LangGraph flat spine,
pure `run()` stage logic, Protocol-fronted service adapters, HITL retry
controls, and the Pathling/code-search service adapters.
**Specifically for concept ports**, `scripts/sofa_provisioning/` shows the
canonical **ViewDefinition structure** — `v_observation.viewdefinition.json` is
the reference for the `select[].column[].{path, name}` shape with
`forEach`/`forEachOrNull`. Take the structure and nothing else: its
provisioning code registers resources against a Pathling server over HTTP,
which this loop does not do. Do **not** copy its BFF, pipeline state, or
gold-standard files.

### `../master_thesis_pipeline/paper_reproductions`

Provides the proven auto-repro loop pattern: orchestrator → subagent
topology, terminal-state markers, convergence judge separation, and the
`MIMIC_NOTES.md` dataset-quirks knowledge base. **Reuse** the loop pattern,
the judger separation, and the code-search service at `localhost:3000`.
Do **not** reuse its terminology-resolution stage: this loop resolves no codes
(see Coding policy).
Its `common/executor.py` is the proven embedded-Pathling pattern this repo's
`embedded_runner` follows. Do **not** copy destructive `git checkout`
behaviours, `tmp/` scratch-as-state patterns, or prompt-only state.

**HPC conventions are no longer read from there.** The `hpc-transfer` and
`csiro-hpc` skills now live in this repo under `.opencode/skills/`, adapted
to the concept-port layout, and the transfer/submit/poll/fetch logic is code
in `src/mimic_utils/hpc.py`. Never follow a `../master_thesis_pipeline/...`
path for cluster details — that cross-repo dependency was deliberately cut.

---

---

## Coding policy

**A concept's codes are the ones its source SQL names. Lift them; do not map
them.**

1. **The source SQL is the specification.** Whatever `itemid`, ICD code, or
   coding system `mimic-iv/concepts/<concept>.sql` filters on is the code set
   for the port. `source-analyst` extracts those literals verbatim — no
   normalization, no expansion, no substitution.
2. **The FHIR side stores the same values.** For every itemid-derived
   `Observation` stream the MIMIC-on-FHIR ETL writes
   `code.coding.code = CAST(itemid AS TEXT)` and joins the dimension table only
   for `display`. So `CAST(code AS INTEGER)` recovers the itemid, and that is
   the entire mapping. Verified against the demo warehouse and the ETL SQL —
   see `MIMIC_NOTES.md`.
3. **Discriminate on `code.coding.system` + exact code.** Never on
   `meta.profile`: the merged data preparation collapses profile values across
   the Observation sub-profiles, so a profile that discriminates in one
   warehouse variant does not in another.
4. **No terminology service, no runtime translation.** The loop calls no
   `$translate`, `$expand`, or `$lookup`, and authors no `translate()` into a
   ViewDefinition. The oracle is relational MIMIC-IV keyed on the same codes,
   so translation could only subtract. It is also unavailable where it would
   matter: the HPC compute nodes that run the deciding comparison have no
   internet.
5. **Some streams are natively standard-coded.** ED vital-signs Observations
   carry LOINC and no itemid at all, because the ETL hardcodes those codes.
   That is not an exception to rule 1 — it is still "whatever the data carries,
   established by probing". `fhir-prober` confirms; nothing translates.

---

## Deterministic comparator

The `concept-equivalence` skill runs a deterministic comparator that gates
convergence. It runs at two different strengths depending on the dataset.

### Demo — shape only

Executed locally in seconds. Gates:

- **Execution** — the ViewDefinition and SQL run at all.
- **Column name identity** — same column names as the oracle.
- **Column type compatibility** — DuckDB vs Spark/Pathling type names
  normalized.

Row count is **not** gated on demo, and **0 demo rows yields `unsure`**, not
`fail` — the 100-patient cohort legitimately contains nothing for some
concepts. Demo agreement is not evidence of correctness; demo disagreement on
shape is a cheap, real bug report.

### Full data — correctness

Executed on HPC against the immutable full oracle.

- **Column schema identity** — same column names and types. **Hard gate.**
- **Keyed row-level diff** — full outer join on the concept's natural key from
  `oracle_manifest.full.json`, then per-column value comparison. Concepts with
  no unique key are compared as full-tuple multisets.
- **Row count** — reported, **not gated**. MIMIC-on-FHIR does not carry
  everything relational MIMIC-IV carries, so a faithful port can legitimately
  return fewer rows.

Per-column min/max identity is **not** sufficient evidence of equivalence: a
port that assigns every correct value to the wrong key satisfies it. The keyed
diff is what substantiates the claim.

Because row count is not a gate, the diff **classifies** every divergence
rather than merely counting it, and the verdict follows from the classes:

| Class | Can a MIMIC-on-FHIR coverage gap cause it? | Tier it forces |
|---|---|---|
| `only_oracle` | yes — this is what a gap looks like | `gap_shaped` |
| `differing_null_only` | yes — the FHIR element does not exist | `gap_shaped` |
| `only_candidate` | no — fan-out or a wrong filter | `contested` |
| `differing_conflict` | no — the row exists on both sides | `contested` |
| `false_unrepresentable_declaration` | no — the port's claim and its own data contradict | `mismatch`, no judge |

- `match` — nothing diverged. The judge is **never** called.
- `mismatch` — a machine-provable contradiction: the candidate did not
  execute, the schema is wrong, or a declaration its own data refutes. The
  judge **cannot** override it, because there is nothing to weigh.
- `review` — anything else that diverged. Not a pass, not a failure. The
  **judge decides**, at the bar its tier sets. There is no size threshold: a
  divergence of any magnitude reaches the judge, and none of any magnitude
  auto-accepts.

**A conflict is not a hard failure.** It was until 2026-08-07, on the reasoning
that a coverage gap cannot cause one — true, but a gap is not the only thing
MIMIC-on-FHIR does to MIMIC-IV. It also rewrites values (`fhir_patient.sql:15`
synthesises `birthDate` from `MIN(transfers.intime)`; `fhir_encounter.sql:65`
DST-shifts admission times), and no port can invert either. So a conflict
raises the bar instead of failing the port: a `contested` review must cite the
upstream ETL statement, file and line, and show the oracle value is
unrecoverable by any query. Without that citation the answer is `bug` and the
loop continues as before. A conflict still outranks a gap — a result with both
is `contested`.

The class lists above are defined in `src/mimic_utils/compare_port_results.py`
(`_GAP_CLASSES`, `_CONTESTED_CLASSES`, `_UNRESOLVABLE_CLASSES`), and
`mimic-iv/concepts_fhir/LOOP_CONTRACT.md` is authoritative on what they mean.

The 13 unkeyed concepts cannot have their classes separated (a NULL-for-value
divergence is indistinguishable from an invented row without a key). Those
route to `review` carrying `classification: unavailable_no_key`, and the judge
is told it is reasoning with less evidence than usual.

---

## Scope: this is a one-off research pipeline, not a product

This repo's concept-port loop exists to produce **convergence results** for one
research question. It is not a production application and is not maintained as
one. Judge every change by whether it moves a concept toward a defensible
full-data verdict.

- **Do not write tests for the pipeline code.** No unit tests, no regression
  suites, no coverage goals for `src/mimic_utils/` port machinery. Time spent
  there is time not spent converging concepts. The existing `tests/` directory
  is legacy from upstream MIMIC-code plus a few files that already exist —
  leave them alone, do not extend them, and do not add new test files.
- **Verify by running the thing.** The evidence that code works is a demo shape
  gate that executes and a full-data comparison artifact, not a green test run.
  If a change needs checking, run `mimic_utils run-demo` or `run-full` on a real
  concept and read the artifact.
- **Exception — a bug that changes a verdict.** If something would make the loop
  reach a *wrong* conclusion (a concept blocked that should have proceeded, a
  mismatch reported as a match), fix it and say so plainly in the evidence
  block. Correctness of the comparison is the one thing that is not negotiable,
  because it is the entire output of the project.
- **No polish work.** Do not refactor for elegance, rename for consistency, or
  restructure modules that already work. Prefer the smallest change that gets a
  concept to a verdict.

## Rules for all agents

- **No git commits.** Never run `git commit`, `git push`, `git tag`, or
  `git merge`. The working tree tracks state through files only.
- **No destructive reverts.** Never run `git checkout -- <file>` to revert
  an earlier attempt. Immutable attempts: each version is a new directory.
- **Immutable attempts.** Attempt artifacts are write-once. Files may be
  added once while the attempt runs, but no existing file is edited or
  replaced. A fix creates a new attempt via `mimic_utils retry`. Only the
  orchestrator may promote a converged attempt to canonical.
  **Two locations sit outside this regime**, neither an attempt artifact: they
  record what stays true after an attempt is superseded.
  `mimic-iv/concepts_fhir/MIMIC_NOTES.d/<concept>.md` (shared dataset knowledge
  — **append-only**, new sections at the end, earlier ones never rewritten; see
  "Shared dataset knowledge" above) and
  `mimic-iv/concepts_fhir/carryover/<concept>/` (per-concept analysis reused
  across attempts — **overwritten in place**, unchanged by any of this; see
  "Carryover" below). `MIMIC_NOTES.md` itself is read-only to a loop.
- **Output evidence.** Every subagent response ends with a plain-prose
  evidence block: what was read, what was checked, the result, and the
  artifact paths produced. The orchestrator stores each block once under
  `attempt_NNNN/evidence/<stage>.md`; it never appends to an existing file.
- **Sequential execution within a goal.** Only one concept is ported per
  `/goal`. The orchestrator never starts the next concept without an explicit
  new `/goal`. Parallel subagent execution is prohibited unless the user
  explicitly requests it in the goal text.
- **Terminal markers.** At goal completion, the orchestrator must emit a
  final evidence block and signal the terminal state: `[goal:complete]` on
  success or `[goal:blocked]` on a representability exception.

---

## Skills

| Skill | Use for |
|-------|---------|
| `concept-orchestrator-loop` | The primary loop: receive concept → DAG validate via `mimic_utils init/start` → schedule subagents → gate → converge/judge → append new dataset quirks to `MIMIC_NOTES.d/<concept>.md` |
| `concept-dag` | Reading and validating `concept_dag.json` — nodes dict, edges list, topological_order, levels, full 64-char SHA256 verification |
| `fhir-mapping` | Mapping MIMIC source tables/columns to FHIR paths + authoring ViewDefinitions (select.column path/name + forEach/forEachOrNull patterns) |
| `vcl` | Writing/interpreting FHIR ValueSet Compose Language expressions and `http://fhir.org/VCL?v1=...` implicit ValueSet URLs — operators, filters, percent-encoding, `compose` mapping |
| `pathling-sql` | Authoring ViewDefinitions and `concept.sql` for embedded Pathling on Spark: the label-is-the-table-name invariant, the Spark SQL dialect notes this warehouse needs, and the shape contract |
| `concept-equivalence` | Running the deterministic comparator — shape only on demo (`pass`/`fail`/`unsure`), schema identity + the classified keyed row-level diff on full data (`match`/`mismatch`/`review`, with a tier on every `review`); row count reported, never gated |
| `hpc-transfer` | The full-data leg: `hpc-launch` / `hpc-poll`, what the embedded job does on the node, and the artifact contract. Self-contained in this repo |
| `csiro-hpc` | Petrichor/Virga cluster conventions: node sizes, no internet on compute nodes, scratch3 rules, the sanctioned 5-minute polling exception |
