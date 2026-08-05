# AGENTS.md — MIMIC-IV → MIMIC-on-FHIR concept port

This repo holds the canonical MIMIC-code concept library. The active task is a
**sequential, one-concept-at-a-time** port of MIMIC-IV concepts (SQL views over
raw `mimiciv_hosp` / `mimiciv_icu` tables) into MIMIC-on-FHIR representations
(FHIR ViewDefinitions + Pathling-derived SQL).

Read this once. The orchestrator, subagents, and skills referred to here are
defined under `.opencode/` and are loaded automatically. External reference
repos — `../master_thesis_pipeline/orchestration-new` and
`../master_thesis_pipeline/paper_reproductions` — provide proven patterns and
terminology infrastructure; consult them for conventions, but do not copy
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
    concept_dag.md                 # human-readable DAG reference
  buildmimic/                      # dialect-specific build scripts (postgres, duckdb, …)
  concepts_fhir/                   # FHIR port output directory
    concepts/<category>/<concept>/ # per-concept port dir
      attempt_NNNN/                # immutable attempt subdirectories
    state/<concept>/state.json     # ConversionController state
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
4. **Terminology resolver** resolves source coding systems and codes against
   Velonto FHIR ConceptMaps (see Terminology policy below).
5. **Implementer** authors the FHIR ViewDefinition and derived SQL.
6. **Demo runner** executes the ViewDefinition + SQL against the local demo
   Pathling instance. This is a **cheap shape gate, not a correctness gate**:
   it catches execution failure, wrong column names, and incompatible types.
   Row count is **not** a demo gate, and **0 demo rows is `unsure`, never
   `fail`** — proceed to full data.
7. **Full runner** executes the attempt on full data via the HPC launch/poll
   flow and compares it against the immutable full oracle. This is where
   correctness is decided: exact row count, schema, and the keyed diff. The
   agent may submit **as many full runs as it judges necessary**, up to a
   **hard cap of 10 per concept**.
8. **Mismatch diagnostician** (if mismatch) diagnoses root cause from the
   keyed diff. The implementer modifies only the ViewDefinition/SQL in a new
   immutable attempt; previous attempts are never rewritten. Then loop back
   to step 6.
9. **Equivalence judge** assesses *only* representability exceptions (a
   concept that cannot be perfectly expressed in FHIR even after all
   defensible mappings are tried). The judge is **never called** for an
   ordinary passing comparator unless a separate audit is desired. The judge
   cannot override hard gate failures. A `representable` verdict means the
   gap is intrinsic to the IG, not a bug.
10. The concept completes only when the **full-data** hard gates pass. A demo
    pass earns nothing except permission to spend an HPC run. A
    judge-confirmed intrinsic representability gap is a documented blocked
    terminal state, not a passing comparison. Reaching 10 full runs without
    convergence terminates the concept for human review.

`mimic-iv/concepts_fhir/LOOP_CONTRACT.md` is the authoritative statement of
what is compared, where, and what gates what. If this file or any skill
disagrees with it, the contract wins and the other document is a bug.

Do not commit, push, or create PRs. Each attempt is immutable in its own
attempt subdirectory. State is managed by the `ConversionController` via
`mimic_utils init|start|validate-demo|validate-full|done|fail|block` CLI
commands. In an unactivated shell, prefix every command with `uv run`, for
example `uv run mimic_utils status`.

---

## Artifact layout

State is managed by `ConversionController` (`src/mimic_utils/conversion_state.py`)
and its CLI (`mimic_utils init|start|validate-demo|...`). The canonical paths:

```
{repo_root}/mimic-iv/concepts_fhir/
  state/<concept>/state.json                    # ConversionController state
  concepts/<category>/<concept>/attempt_NNNN/   # immutable attempt dirs
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
  5. `mimic_utils done <concept>` — COMPLETED
  6. `mimic_utils fail <concept> --error "..."` — FAILED
  7. `mimic_utils block <concept> --error "..."` —
     BLOCKED_REPRESENTATION pending human review

---

## External references

### `../master_thesis_pipeline/orchestration-new`

Provides the proven agentic pipeline architecture: LangGraph flat spine,
pure `run()` stage logic, Protocol-fronted service adapters, HITL retry
controls, and the Pathling/code-search/terminology service adapters.
**Specifically for concept ports**, the `scripts/sofa_provisioning/`
directory shows the canonical ViewDefinition/Library provisioning pattern:
register a ViewDefinition via PUT, register a sql-view Library with
`relatedArtifact` labels referencing the ViewDefinition, and execute
through `$sqlquery-run`. Do **not** copy its BFF, pipeline state, or
gold-standard files.

### `../master_thesis_pipeline/paper_reproductions`

Provides the proven auto-repro loop pattern: orchestrator → subagent
topology, terminal-state markers, convergence judge separation, HPC
transfer/poll, and the `MIMIC_NOTES.md` dataset-quirks knowledge base.
**Reuse** the loop pattern, the judger separation, and the terminology
infrastructure (code-search at `localhost:3000`, Velonto TX server at
`https://velonto.dw.csiro.au/fhir`). **Specifically**, the `hpc-transfer`
and `csiro-hpc` skills in `.claude/skills/` are the authoritative
reference for HPC transfer conventions. Do **not** copy destructive
`git checkout` behaviours, `tmp/` scratch-as-state patterns, or
prompt-only state.

---

## Agent model tiers

| Tier | Agents | Model |
|------|--------|-------|
| **Complex** | `concept-port-orchestrator`, `concept-implementer`, `mismatch-diagnostician`, `equivalence-judge` | `openai/gpt-5.6-sol` variant `xhigh` |
| **Bounded analysis** | `source-analyst`, `fhir-prober`, `terminology-resolver`, `engineering-debugger` | `openai/gpt-5.6-luna` variant `xhigh` or `max` |
| **Mechanical** | `dag-checker`, `demo-runner`, `hpc-launcher`, `hpc-poller` | `openai/gpt-5.6-luna` variant `low` |

---

## Terminology policy

1. **Velonto FHIR ConceptMaps are authoritative.** All terminology resolution
   starts and ends at `https://velonto.dw.csiro.au/fhir`. Local copies are
   snapshots for reproducibility only.
2. **Source coding system + code first.** Identify the MIMIC source coding
   system (e.g. `http://hl7.org/fhir/sid/icd-9-cm`,
   `http://loinc.org`) and code from the concept SQL before consulting
   any mapping table.
3. **Accept every actual ConceptMap relationship except explicit `unmatched`.**
   A ConceptMap entry with an explicit `equivalence: unmatched` is the only
   refusal condition. A missing target (no mapping found) remains **unresolved**
   — it is not the same as unmatched; it means the ConceptMap has no entry for
   that source code at all.
4. **Explicit canonical for production `translate()`.** Every production
   `translate()` call in a ViewDefinition cites the exact ConceptMap
   canonical URL. The version is **separately** preflight-asserted before
   production use, because `url|version` is not a valid translate parameter
   — the server resolves by URL alone, and we verify the version match
   out-of-band.
5. **Preflight scope / version / content hash.** Before production use of a
   ConceptMap, fetch and record its `version`, `date`, and a full SHA256 of
   the complete FHIR JSON content. This hash is written into the concept's
   port directory for later reproducibility audit.
6. **Local FHIR JSON snapshots.** Snapshot every ConceptMap and ValueSet used
   by a concept port into the concept's port directory as `.fhir.json` files
   (the complete FHIR JSON resource). These are the ground truth for reruns;
   the live server may change.

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

Executed on HPC against the immutable full oracle. Hard gates:

- **Row count identity** — **exact match required**. Floating-point tolerances
  apply only to per-column value comparisons, never to row count.
- **Column schema identity** — same column names and types.
- **Keyed row-level diff** — full outer join on the concept's natural key from
  `oracle_manifest.full.json`, then per-column value comparison. Reports rows
  only-in-oracle, only-in-candidate, matched-but-differing (and *which* column
  differs), and identical. Concepts with no unique key are compared as
  full-tuple multisets.

Per-column min/max identity is **not** sufficient evidence of equivalence: a
port that assigns every correct value to the wrong key satisfies it. The keyed
diff is what substantiates the claim.

Hard gate failures produce `mismatch` — the judge **cannot** override them.
The judge may assess only **representability exceptions**: a concept that,
after all defensible FHIR mappings are exhausted, still cannot produce an
identical result row set due to intrinsic IG limitations. Each exception
must cite a specific FHIR element or path that lacks an equivalent.
The judge is **never** called for an ordinary passing comparator.

---

## Rules for all agents

- **No git commits.** Never run `git commit`, `git push`, `git tag`, or
  `git merge`. The working tree tracks state through files only.
- **No destructive reverts.** Never run `git checkout -- <file>` to revert
  an earlier attempt. Immutable attempts: each version is a new directory.
- **Immutable attempts.** Attempt artifacts are write-once. Files may be
  added once while the attempt runs, but no existing file is edited or
  replaced. A fix creates a new attempt via `mimic_utils retry`. Only the
  orchestrator may promote a converged attempt to canonical.
- **Output evidence.** Every subagent response ends with a plain-prose
  evidence block: what was read, what was checked, the result, and the
  artifact paths produced. The orchestrator stores each block once under
  `attempt_NNNN/evidence/<stage>.md`; it never appends to an existing file.
- **Sequential execution.** Only one concept is ported per `/goal`. The
  orchestrator never starts the next concept without an explicit new `/goal`.
  Parallel subagent execution is prohibited unless the user explicitly
  requests it in the goal text.
- **Terminal markers.** At goal completion, the orchestrator must emit a
  final evidence block and signal the terminal state: `[goal:complete]` on
  success or `[goal:blocked]` on a representability exception.

---

## Skills

| Skill | Use for |
|-------|---------|
| `concept-orchestrator-loop` | The primary loop: receive concept → DAG validate via `mimic_utils init/start` → schedule subagents → gate → converge/judge |
| `concept-dag` | Reading and validating `concept_dag.json` — nodes dict, edges list, topological_order, levels, full 64-char SHA256 verification |
| `fhir-mapping` | Mapping MIMIC source tables/columns to FHIR paths + authoring ViewDefinitions (select.column path/name + forEach/forEachOrNull patterns) |
| `velonto-maps` | Terminology resolution via Velonto ConceptMaps at `https://velonto.dw.csiro.au/fhir`: `$translate`, `$expand`, VCL implicit ValueSets |
| `pathling-sql` | Registering ViewDefinitions, registering sql-view Libraries with relatedArtifact labels, deriving+executing SQL via `$sqlquery-run` |
| `concept-equivalence` | Running the deterministic comparator — shape only on demo, exact row count + schema + keyed row-level diff on full data — producing `match`/`mismatch`/`unsure` |
| `hpc-transfer` | Staging a concept port to the HPC for full-MIMIC execution (defer to paper_reproductions csiro-hpc/hpc-transfer skills for conventions) |
