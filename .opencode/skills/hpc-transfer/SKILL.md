---
name: hpc-transfer
description: Run a concept-port attempt on full MIMIC on the CSIRO HPC (Petrichor) — stage the attempt to scratch3, smoke-test the remote environment, submit the Slurm job, poll it, and fetch the verdict back. This is the full-data correctness gate, the only gate that can complete a concept. Trigger phrases include "run on full data", "transfer to HPC", "submit to Petrichor", "launch the full run", "poll the job", "fetch HPC results".
---

# hpc-transfer

The full-data leg of the concept-port loop. Demo only rejects malformed ports;
**this is where correctness is decided**, and a concept cannot reach
`COMPLETED` without a full-data `match` produced here.

Several concepts are ported at once, so several jobs may be in the queue. Two
consequences run through everything below: **each attempt stages its own copy
of the code and the manifest**, and **you only ever touch your own job id**.

Cluster conventions (node sizes, no internet on compute nodes, scratch3 rules)
live in the `csiro-hpc` skill. This skill is authoritative for everything
concept-port specific. Both are in this repo — nothing here defers to
`../master_thesis_pipeline`.

## Use the CLI, never hand-written ssh

Every step is implemented in `src/mimic_utils/hpc.py`. Call it:

```bash
uv run mimic_utils hpc-launch <concept>    # stage + smoke test + sbatch
uv run mimic_utils hpc-poll   <concept>    # poll every 5 min, then fetch
```

An agent that writes its own `ssh ... rsync ...` or `ssh ... squeue` loop is
doing it wrong: that is how invocations drift between runs and how a verdict
ends up unreproducible. If the CLI cannot express something, fix the CLI.

## What actually runs on the node

There is **no Pathling server in this path**. Compute nodes have no internet and
no FHIR server, so the job embeds Pathling in-process over PySpark
(`PathlingContext.create()`, `ctx.read.delta(warehouse)`), reading the Delta
warehouse directly. The candidate and the oracle are both node-local, so
nothing moves during the comparison.

Inside one job:

1. Each `ViewDefinition.<label>.json` is materialised as a Spark temp view named
   `<label>` — the same label -> table binding the server backend gets from a
   `depends-on` relatedArtifact, so `concept.sql` is byte-identical either way.
2. `concept.sql` runs and is written to `candidate.full.parquet`.
3. `compare_full` opens the oracle **read-only** and runs the keyed row-level
   diff entirely as DuckDB SQL. Rows are never materialised into Python —
   `vitalsign` is 9.7M rows.

The oracle is **never rebuilt**. It was computed once by
`mimic_utils.build_full_oracle`; a job that recomputed it would be comparing the
port against itself.

## Fixed facts

| What | Value |
|---|---|
| SSH target | `nau025@petrichor.hpc.csiro.au` (key-based, prompt-free) |
| Remote mirror root | `/scratch3/nau025/mimic-code` (attempt paths mirror this repo's tree under it; **not** a shared code tree — see below) |
| Remote env project | `/scratch3/nau025/mimic-on-fhir-delta` (uv env with pathling + pyspark + duckdb) |
| Full FHIR warehouse | `/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse` (156 GB Delta) |
| Full oracle | `/scratch3/nau025/oracle/mimic4-full.db` (14.5 GB DuckDB, read-only) |
| Account | `OD-221174` |
| Wall time | `2:00:00` |
| Modules | `python/3.12.3`, `amazon-corretto/21.0.0.35.1` |
| Slurm template | `mimic-iv/concepts_fhir/submit_concept_run.slurm` |
| CPUs | `--ntasks=1 --cpus-per-task=32` (one JVM, not 64 MPI ranks) |
| Memory | `--mem=256g`, with `spark.driver.memory=200g` |
| Spark master | `local[32]`, `spark.driver.maxResultSize=16g` |
| Shuffle partitions | `256` (`spark.sql.shuffle.partitions`, `spark.default.parallelism`) |

Half a node, deliberately: concurrent concept runs then co-schedule instead of
each queueing for a whole node. `sacct` over the first ten jobs shows peak
MaxRSS 172.5 GiB (`antibiotic`) and elapsed 23 s – 2 m 27 s. Two caveats keep
that honest — those were the five *lightest* concepts (heaviest 735 K rows,
while `vitalsign` is 9.7 M and `sofa` 6.0 M, both unrun), and a MaxRSS measured
under a 400 GB heap is partly an artifact of the ceiling (`acei` used 76 GiB and
128 GiB on two runs of identical data).

`--mem` ↔ `spark.driver.memory` and `--cpus-per-task` ↔ `local[N]` are **coupled
pairs**. Raise or lower both halves together: a heap larger than `--mem` gets
the job SIGKILLed by cgroups with no traceback, which reads as a mystery crash
rather than a sizing mistake. The 256 partition counts stay as they are;
lowering them without measuring is a guess.

Every value is overridable by env (`MIMIC_HPC_HOST`, `MIMIC_HPC_ACCOUNT`, …)
— see the constants at the top of `src/mimic_utils/hpc.py`.

The job runs `uv run --no-sync` from the env project with
`PYTHONPATH=$ATTEMPT_DIR/src`, so it uses that env's pathling/pyspark but **the
attempt's own staged copy** of this repo's code. `--no-sync` is mandatory: a
sync would try to reach the network and fail on a compute node.

Add this to `~/.ssh/config` for the host — every step opens its own connection,
and several goals launch and poll at once:

```
Host petrichor.hpc.csiro.au
    ControlMaster auto
    ControlPath ~/.ssh/cm-%r@%h:%p
    ControlPersist 60s
```

### One-time setup (login node, already done manually)

```bash
cd /scratch3/nau025/mimic-on-fhir-delta && uv pip install duckdb==1.5.5
```

Compute nodes have no internet, so nothing may download at job time. There is
deliberately **no `preflight-hpc` command**: SSH access, the env and the
warehouse do not drift within a session, so they are confirmed once by hand.
What *is* checked every launch is the login-node smoke test below.

## Launch

`hpc-launch` does four things, in this order, and stops at the first failure:

1. **Render** `submit.slurm` from the template into the attempt directory, so
   what ran is recoverable from the artifacts afterwards.
2. **Stage** three rsyncs, all into the attempt's **own** remote directory:
   `src/mimic_utils/` → `<remote_attempt>/src/mimic_utils/`, the oracle manifest
   → `<remote_attempt>/oracle_manifest.full.json`, and the attempt itself.
   Result artifacts are excluded from the upload, so anything named
   `comparison.full.json` on the remote is unambiguously produced there.
3. **Smoke-test** on the login node, against the staged copy: warehouse present,
   oracle present, staged manifest present, and
   `import duckdb, pathling, pyspark, mimic_utils.full_runner` resolves under
   `PYTHONPATH=<remote_attempt>/src`. It deliberately does **not** create a
   `PathlingContext` — that is a heavy JVM on a shared login node.
4. **Submit** and record the job id in `hpc_job.json`.

**Why per attempt rather than one shared tree.** Two failures, both silent.
A job launched at 14:00 lazily imports `compare_port_results` at 14:22 and picks
up whatever another loop staged at 14:10 — a verdict produced by two code
versions, recorded nowhere. And the code rsync uses `--delete`: into a shared
destination, two concurrent launches delete and rewrite the module tree a third
job is importing. The side benefit is that `attempt_NNNN/` becomes
self-describing — the code that produced the verdict is part of the evidence.

**A failed smoke test never reaches `sbatch`**: a broken job still costs a queue
slot. One attempt carries at most one full run — `hpc_job.json` is write-once,
so a second full run means a new attempt.

## Poll and fetch

`hpc-poll` checks `squeue -u $USER` every 300 s and greps the job log for
`Traceback|OutOfMemory|slurmstepd|CANCELLED|Error`, breaking early on any of
them. Then it fetches `comparison.full.json` and `run_meta.full.json` back into
the attempt directory and writes `hpc_accounting.json` from the completed
allocation's `sacct` record. This captures actual Slurm elapsed runtime without
counting queue or polling time.

**`squeue -u $USER` lists sibling concepts' jobs too.** Read exactly one id out
of it — yours, from `hpc_job.json` — and ignore every other line. **Never
`scancel` a job whose id is not the one in your own `hpc_job.json`**, however
stuck the queue looks: the other ids belong to other goals, and cancelling one
destroys an attempt that is not yours and spends one of its ten runs.

**Leaving the queue is not success.** A job that OOMs also leaves the queue, so
the outcome is decided by whether a comparison artifact exists:

| Outcome | Meaning |
|---|---|
| `complete` | comparison fetched; read its `verdict` (`match` / `mismatch`) |
| `crash` | queue exited with no comparison; the Slurm log is fetched for diagnosis |
| `timeout` | still queued after the poll budget |

`candidate.full.parquet` is deliberately **left on scratch** — it can be
hundreds of MB and the verdict does not need it locally.

A `mismatch` is a verdict, not a job failure: the Slurm script exits 0 whenever
a comparison was produced, so a FAIL email means "no verdict", nothing else.

## Artifacts

Written into `mimic-iv/concepts_fhir/concepts/<category>/<concept>/attempt_NNNN/`:

| File | Where written | Fetched |
|---|---|---|
| `submit.slurm` | locally at launch | — |
| `hpc_job.json` | locally at launch (job id, remote path) | — |
| `hpc_accounting.json` | locally at poll completion from `sacct` | — |
| `candidate.full.parquet` | remote | no (stays on scratch) |
| `comparison.full.json` | remote | **yes — the verdict** |
| `run_meta.full.json` | remote | yes |
| `slurm-<jobid>.out` | remote | only on crash |

All write-once. A fix is a new attempt, never an edit.
