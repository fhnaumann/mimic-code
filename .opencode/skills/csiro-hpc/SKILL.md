---
name: csiro-hpc
description: Guide for running jobs on CSIRO HPC clusters (Petrichor and Virga) using Slurm. Use this skill when submitting batch jobs, writing Slurm job scripts, transferring data to scratch, loading environment modules, requesting GPUs, or working with the CSIRO HPC systems. Trigger keywords include "HPC", "Petrichor", "Virga", "Slurm", "sbatch", "sinteractive", "batch job", "GPU job", "scratch3", "module load", "cluster job".
---

# CSIRO HPC

## Clusters

- **Petrichor** (`petrichor.hpc.csiro.au`) - general purpose CPU cluster. 64 cores and 512 GB RAM per node. Use by default.
- **Virga** (`virga.hpc.csiro.au`) - GPU accelerator cluster with 4x NVIDIA H100 GPUs per node, 72 cores and 512 GB RAM per node. Use only when the job benefits from GPU acceleration.

## Mandatory pre-submission checklist

For the concept port these are already fixed and need no prompting: account
`OD-221174`, input and output both under `/scratch3/nau025`. For any *other*
job, collect from the user:

1. **O2D project code** (format: `OD-XXXXXX`). Use `--account=<code>`.
2. **Input data location** - confirm it is on `$SCRATCH3DIR`; stage it there first if not.
3. **Output data location** - all output must be written to `$SCRATCH3DIR`.
4. **Timezone** - if the job touches a timestamp at all, `export TZ=UTC` (plus
   `--conf spark.sql.session.timeZone=UTC` for Spark). Not negotiable and not a
   user question; see "Pin the timezone" below.

Before submitting a job, validate the execution environment on the login node. Run a minimal smoke test (e.g. a short Python import check, verify JAR dependencies resolve) to catch issues like missing packages, wrong Python version, or uncached artifacts. Each failed job wastes cluster allocation time. `mimic_utils hpc-launch` does this automatically and refuses to `sbatch` when the smoke test fails.

## Job script conventions

Always request all resources on the node(s) you allocate - there is no benefit to requesting a partial node. Use `--exclusive` to claim the entire node.

- **Petrichor:** 64 cores, 503 GB usable RAM per node.
- **Virga:** 72 cores, 512 GB usable RAM, 4 GPUs per node.

**Exception — the concept-port full run.** `mimic-iv/concepts_fhir/submit_concept_run.slurm` deliberately asks for **half a node** (`--ntasks=1 --cpus-per-task=32 --mem=256g`, no `--exclusive`). The rule above assumes one job at a time; that loop runs several concepts in parallel, so whole-node requests make siblings queue behind each other instead of co-scheduling, and measured peak usage is well inside half a node. Do **not** "repair" that template back to 64 cores / 503g / `--exclusive`. Its sizing and its rationale are in `.opencode/skills/hpc-transfer/SKILL.md`; `--mem` ↔ `spark.driver.memory` and `--cpus-per-task` ↔ `local[N]` are coupled pairs and move together. The oracle build (`concepts_fhir/oracle/submit_build_oracle.slurm`) is a single whole-node job and correctly follows the rule.

### Pin the timezone — mandatory for every job that touches a timestamp

**Both clusters run with system zone `Australia/Sydney`.** Any job that reads,
writes, formats or compares a wall-clock value must pin the zone explicitly.
Add these two lines to every such job script, before the workload starts:

```bash
export TZ=UTC                                   # before any JVM starts
# ... and for Spark, additionally:
--conf spark.sql.session.timeZone=UTC
```

Set **both**, not either. `TZ` fixes the zone the JVM samples at boot — which is
where Spark *derives* its default `spark.sql.session.timeZone` — and it also
governs DuckDB and Python `datetime` in the same process. The `--conf` is what
survives someone exporting a different `TZ` further down the script.

**Why this is not optional.** In Spark 4.0.2, `DATE_FORMAT` and `DATE_TRUNC`
consult the session zone *even for a zone-less `TIMESTAMP_NTZ`*, and silently
push a wall time that falls in that zone's DST spring-forward gap an hour
forward. Measured on Petrichor:

| expression on `TIMESTAMP_NTZ`, session zone `Australia/Sydney` | `2140-10-02 02:00` |
|---|---|
| `CAST(… AS STRING)` | `02:00:00` ✅ |
| `DATE_FORMAT(…, 'yyyy-MM-dd HH:mm:ss')` | `03:00:00` ❌ |
| `DATE_TRUNC('HOUR', …)` | `03:00:00` ❌ |

02:00–03:00 on the first Sunday in October does not exist in Sydney. MIMIC
timestamps are de-identified *wall clocks*, not instants, so this corrupts data
that was never in a timezone to begin with. It cost the concept-port loop six
concepts' worth of UUID-inversion workarounds against a defect that was never in
the data — see `mimic-iv/concepts_fhir/TODO_warehouse_rebuild.md`.

**`UTC`, not `America/New_York`.** UTC has no DST in any year, so no wall clock
can be normalised by accident. Matching the source zone would still leave the
March gap live.

**Pin it in the environment, not in the SQL.** A generated query is reviewed
once and the failure mode is invisible — the wrong answer is well-formed, off by
exactly one hour, on a handful of rows a year. In this repo the Spark half is
enforced at the single point where the JVM is created
(`_pin_session_timezone` / `SESSION_TIMEZONE` in `src/mimic_utils/embedded_runner.py`),
so it covers the local demo leg and the HPC leg identically. **Never rely on a
`concept.sql` to set its own zone**, and treat a job script that starts a JVM
without `export TZ` as incomplete.

Both legs must use the *same* zone. Pinning only the Slurm side would make the
local demo run (Sydney laptop) and the full run (UTC node) disagree, which
converts a config bug into a phantom port bug.

Choose wall time based on estimated job duration. Default to 2 hours unless the user indicates the job needs longer, or the workload clearly requires it (e.g. deep learning training, very large datasets).

- **Short jobs** (quick tests, small data, simple processing): `--time=2:00:00`
- **Long jobs** (large datasets, training, multi-step pipelines): `--time=24:00:00`

Always include email notifications:

```
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=Felix.Naumann@csiro.au
```

### CPU job template (Petrichor)

```bash
#!/bin/bash
#SBATCH --job-name=<descriptive-name>
#SBATCH --account=<O2D code>
#SBATCH --time=<2:00:00 or 24:00:00>
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=64
#SBATCH --mem=503g
#SBATCH --exclusive
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=Felix.Naumann@csiro.au

# Load required modules.
module load <software>

# Pin the zone: the node's system zone is Australia/Sydney and no wall-clock
# value may inherit it. Required whenever the job touches a timestamp.
export TZ=UTC
# For Spark, also: --conf spark.sql.session.timeZone=UTC

# Run from scratch3.
cd $SCRATCH3DIR/<project dir>

# Application commands here.
```

### GPU job template (Virga)

```bash
#!/bin/bash
#SBATCH --job-name=<descriptive-name>
#SBATCH --account=<O2D code>
#SBATCH --time=<2:00:00 or 24:00:00>
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=72
#SBATCH --gres=gpu:4
#SBATCH --mem=512g
#SBATCH --exclusive
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=Felix.Naumann@csiro.au

# Load required modules.
module load cuda

# Pin the zone: the node's system zone is Australia/Sydney and no wall-clock
# value may inherit it. Required whenever the job touches a timestamp.
export TZ=UTC

# Run from scratch3.
cd $SCRATCH3DIR/<project dir>

# Application commands here.
```

## Network access

Compute nodes have no internet access. All dependencies (Python packages, Maven/Ivy artifacts, container images) must be downloaded or cached on the login node before job submission. Job scripts must not include any `pip install`, `uv sync`, or similar download commands. This also applies to runtime dependency resolution such as Spark's `spark.jars.packages` (which uses Ivy to download JARs) - run a short Spark session on the login node first to cache the artifacts.

## Data handling

- `$SCRATCH3DIR` is shared across Petrichor and Virga. Stage input data here before running jobs and write output here.
- `$HOME` is separate per cluster. Do not use it for job data.
- For large data transfers, use the data mover node via: `sinteractive -p io -t 2:00:00`

## Cluster selection logic

Use **Petrichor** unless the job involves:

- Deep learning training or inference
- CUDA/GPU-accelerated libraries (cuDNN, TensorRT, etc.)
- Any workload explicitly requiring GPU hardware

In those cases, use **Virga** and add `--gres=gpu:<count>` to the job script.

## Monitoring jobs

A human running a job manually does not poll: the `--mail-type` notifications
already report BEGIN/END/FAIL, and polling a queue by hand wastes login-node
cycles.

**The concept-port loop is the sanctioned exception.** It runs unattended and
cannot advance on an email, so `mimic_utils hpc-poll` checks `squeue -u $USER`
for the captured job id — **no more often than every 5 minutes**. That polling
lives in `src/mimic_utils/hpc.py`, not in agent prose; an agent that finds
itself hand-writing an `ssh ... squeue` loop is doing it wrong and should call
the CLI instead.

## Common operations

- **Check job status:** `squeue -u $USER`
- **Job details:** `scontrol show job <jobid>`
- **Cancel job:** `scancel <jobid>`
- **List modules:** `module avail`
- **Load module:** `module load <name>` or `module load <name>/<version>`
- **List project codes:** `get_project_codes`

## Further reference

See [references/slurm-details.md](references/slurm-details.md) for advanced Slurm options including parallel jobs, array jobs, job dependencies, memory partitions, and interactive sessions.
