---
name: concept-orchestrator-loop
description: Drive the MIMIC-IV to MIMIC-on-FHIR concept port loop — receive one named concept, validate against the DAG via mimic_utils init/start, schedule subagents sequentially (source-analyst → fhir-prober → terminology-resolver → concept-implementer → demo-runner → hpc-launcher/poller → mismatch-diagnostician → equivalence-judge). Demo is a cheap shape gate only; full-data HPC comparison decides correctness, capped at 10 runs per concept. Trigger phrases include "port concept", "convert concept", "migrate concept to FHIR", and the /goal command.
---

# concept-orchestrator-loop

The primary loop for the MIMIC-IV → MIMIC-on-FHIR concept port. This skill
is loaded by `concept-port-orchestrator` and is authoritative for the loop,
subagent topology, wait mechanism, terminal-state markers, and CLI usage.

**On gate semantics, `mimic-iv/concepts_fhir/LOOP_CONTRACT.md` outranks this
file.** Read it first. In short: demo is a cheap shape gate that can only
reject malformed ports (0 rows ⇒ `unsure`, never `fail`); full data on HPC is
the real correctness signal and runs as many times as needed, capped at 10.

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
3. **`mimic_utils start <concept>`** — enforces concurrency (one active
   concept at a time), creates immutable attempt directory at
   `mimic-iv/concepts_fhir/concepts/<category>/<concept>/attempt_NNNN/`,
   transitions to RUNNING. Returns the attempt path.
4. **`mimic_utils validate-demo <concept>`** — freezes implementation
   artifacts and transitions to VALIDATING_DEMO before demo execution.
5. **`mimic_utils validate-full <concept>`** — transitions to VALIDATING_FULL
   before the full-MIMIC HPC execution.
6. **`mimic_utils done <concept>`** — transitions to COMPLETED.
7. **`mimic_utils fail <concept> --error "..."`** — transitions to FAILED.
8. **`mimic_utils block <concept> --error "..."`** — records a
   judge-confirmed representability blocker for human review.
9. **`mimic_utils status`** — full DAG-wide status report.

The controller uses three counters: `semantic`, `engineering`, `hpc`.
Lifecycle: `PENDING → RUNNING → VALIDATING_DEMO → VALIDATING_FULL → COMPLETED`
(with FAILED / SKIPPED terminal branches and FAILED → RUNNING / SKIPPED → RUNNING
retry paths).

## Loop phases

### Phase 0 — Concept intake
Receive exactly one named concept from the `/goal` argument. Never accept
multiple concepts. Never auto-advance to the next concept.

### Phase 1 — DAG validation
Run `mimic_utils init <concept>`. This validates:
- Concept exists in the DAG (`concept_dag.json` `nodes` dict).
- Dependencies are recorded.
- Category is derived from the DAG node `path`.

If `mimic_utils depcheck <concept>` reports unmet dependencies, halt and
report. Do not proceed.

### Phase 2 — Create attempt (start)
Run `mimic_utils start <concept>`. This creates the immutable attempt
directory and records the path. Note: the controller increments the
attempt counter; the directory is `attempt_NNNN/` (zero-padded to 4 digits).

### Phase 3 — Sequential subagent pipeline
Spawn subagents one at a time, each feeding off the output of the previous:

1. **source-analyst** — reads `mimic-iv/concepts/<dag_node_path>.sql`, produces
   structured analysis.
2. **fhir-prober** — maps source tables/columns to FHIR resources/element
   paths using the MIMIC-on-FHIR IG and Pathling `$fhir` endpoint.
3. **terminology-resolver** — resolves source coding systems/codes against
   Velonto at `https://velonto.dw.csiro.au/fhir`, following the terminology
   policy exactly.
4. **concept-implementer** — creates one or more
   `ViewDefinition.<label>.json` files and `concept.sql`
    once in the write-once `attempt_NNNN/` directory, using the proven
   ViewDefinition format (select.column `path`/`name`, `forEach`/`forEachOrNull`)
   and the sql-view Library provisioning pattern from
   `../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/`.

### Phase 4 — Demo shape gate (demo-runner)
Run `mimic_utils validate-demo <concept>` before execution, then spawn
`demo-runner` to execute the port against the **local** demo Pathling
instance. This is a **cheap shape gate, not a correctness gate** — seconds,
no queue. It exists to catch, before an HPC run is spent:

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
   mismatch it reads the keyed diff, which names the differing column.
2. If diagnosis says **representability gap** → go to Phase 7 (judge).
3. If diagnosis says **fixable bug** → run `mimic_utils fail <concept>`,
   then `mimic_utils retry <concept>` to create a new write-once attempt.
   The implementer reads the previous attempt, creates corrected artifacts
   once in the new directory, and loops back to Phase 4.

### Phase 6 — Full-data correctness (the real gate)
Run `mimic_utils validate-full <concept>`, then spawn `hpc-launcher` and
`hpc-poller` sequentially. Require a fresh, successful full-data comparison
artifact — queue exit alone is not success.

The oracle is **already computed**: never recompute the derived concept. The
job compares the candidate against the read-only full oracle at
`/scratch3/nau025/oracle/mimic4-full.db`, node-local beside the FHIR
warehouse. Hard gates:
- **Row count identity** — exact match required.
- **Column schema identity** — same names and types.
- **Keyed row-level diff** — full outer join on the manifest key, then
  per-column comparison; full-tuple multiset for the 13 unkeyed concepts.

This is **not** a one-shot confirmation of a demo-approved answer. The agent
may submit **as many full runs as it judges necessary**, iterating on the diff
each time.

- **All full-data hard gates pass** → run `mimic_utils done <concept>` and go
  to Phase 8.
- **Any full-data hard gate fails** → go to Phase 5.
- **10 full runs reached without convergence** → hard cap. Run
  `mimic_utils fail <concept> --error "full-run cap reached"` and terminate
  with `[goal:blocked]` for human review.

### Phase 7 — Equivalence judge
Spawn `equivalence-judge` **only** for representability exceptions. The judge
is **never** called for an ordinary passing comparator.
- `representable` → gap is intrinsic to IG. Write the exception once, run
  `mimic_utils block <concept> --error "..."`, and terminate with
  `[goal:blocked]`.
- `bug` → judge says the gap is fixable. Loop back to Phase 5.

### Phase 8 — Terminal state
Emit terminal markers:
- `[goal:complete]` only after the **full-data** hard gates pass. A demo pass
  never justifies `[goal:complete]` — it only earns permission to spend an
  HPC run.
- `[goal:blocked]` on a documented representability exception, or on reaching
  the 10-run cap.
- Include a final evidence block summarizing: concept, attempt number, number
  of full runs consumed, verdict, artifact paths.

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

## External service dependencies

- **Pathling FHIR endpoint** — for ViewDefinition registration
  (`PUT ViewDefinition/<id>`), Library registration (`PUT Library/<id>` with
  `relatedArtifact` labels), and `$sqlquery-run`. Config at
  `../master_thesis_pipeline/orchestration-new/config/pathling_config.yaml`.
- **Velonto TX server** — `https://velonto.dw.csiro.au/fhir` for terminology
  operations (`$translate`, `$expand`). Config at
  `../master_thesis_pipeline/orchestration-new/config/terminology_config.yaml`.
- **Code-search** — `http://localhost:3000` for discovering codes from
  clinical text (secondary; primarily for paper reproductions).
- **HPC (Petrichor)** — for full-MIMIC execution. Defer to the
  `hpc-transfer` and `csiro-hpc` skills in
  `../master_thesis_pipeline/paper_reproductions/.claude/skills/`
  for all transfer conventions. Require environment preflight before
  first use.
