#!/bin/bash
#SBATCH --job-name=port-chemistry
#SBATCH --account=OD-221174
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=256g
#SBATCH --output=/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002/slurm-%j.out
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=Felix.Naumann@csiro.au

# Full-data correctness run for one concept-port attempt.
#
# Template. `mimic_utils hpc-launch` renders the double-brace placeholders and
# rsyncs the rendered copy into the remote attempt directory; it is never
# submitted as-is. A rendered script therefore contains no braces at all, which
# is what `render_submit_script` asserts before anything reaches the queue.
#
# Everything this job reads is inside $ATTEMPT_DIR, including the mimic_utils
# code and the oracle manifest. Nothing is read from a path shared with another
# job, because several concepts are ported in parallel: a shared code tree gets
# rewritten under a running job (see `stage_attempt`), and a verdict produced
# half by 14:00's code and half by 14:10's is recorded nowhere.
#
# Everything happens on this one node because both sides of the comparison are
# already here: the 156 GB Delta warehouse and the 14.5 GB DuckDB oracle both
# live on /scratch3. Embedded Pathling evaluates the port, DuckDB runs the
# keyed diff against the oracle, and only two small JSON artifacts travel back.
#
# The oracle is immutable and opened read-only. It is NEVER rebuilt here --
# `mimic_utils.build_full_oracle` computed it once, and a run that recomputed
# it would be comparing the port against itself.
#
# Prerequisites (login node, once -- compute nodes have no internet, so nothing
# below may download anything):
#   cd /scratch3/nau025/mimic-on-fhir-delta && uv pip install duckdb==1.5.5
# The env already carries pathling + pyspark.

set -euo pipefail

ENV_PROJECT=/scratch3/nau025/mimic-on-fhir-delta
ATTEMPT_DIR=/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0002

module load python/3.12.3 amazon-corretto/21.0.0.35.1

# Half a node, not a whole one, so concurrent concept runs co-schedule instead
# of queueing behind each other for 64 cores apiece. sacct over the first ten
# jobs shows peak MaxRSS 172.5 GiB (antibiotic) and elapsed 23s-2m27s. Two
# caveats that keep this honest: those were the five *lightest* concepts
# (heaviest 735k rows, while vitalsign is 9.7M and sofa 6.0M, both unrun), and
# MaxRSS measured under a 400 GB heap is partly an artifact of the ceiling --
# acei used 76 GiB and 128 GiB on two runs of identical data. Raise both halves
# of a pair together if a heavy concept OOMs.
#
# --ntasks=1 --cpus-per-task rather than --ntasks-per-node: this is one JVM,
# not 64 MPI ranks.
#
# --mem <-> spark.driver.memory and --cpus-per-task <-> local[N] are coupled
# pairs. Let the heap exceed --mem and cgroups SIGKILLs the job with no
# traceback, which reads as a mystery crash rather than a sizing mistake.
#
# The driver JVM is sized here, before Spark starts: PathlingContext cannot
# resize a heap that already exists. 200g of the 256g request leaves headroom
# for the DuckDB comparison that runs in the same process afterwards.
#
# The two partition counts stay at 256. They were presumably tuned as 4x64; at
# 32 cores that is 8x, and 8x partitions on a 30-second job costs little.
# Lowering them without measuring would be a guess.
export PYSPARK_SUBMIT_ARGS="--master local[32] \
  --conf spark.driver.memory=200g \
  --conf spark.driver.maxResultSize=16g \
  --conf spark.sql.shuffle.partitions=256 \
  --conf spark.default.parallelism=256 \
  pyspark-shell"

export MIMIC_FHIR_WAREHOUSE=/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse
export MIMIC_FULL_ORACLE=/scratch3/nau025/oracle/mimic4-full.db
export PYTHONPATH="$ATTEMPT_DIR/src"

# Run from the env project so `uv run` resolves its venv, but execute the
# attempt's own staged code via PYTHONPATH -- the same split the oracle build
# used, narrowed to this attempt.
# `--no-sync` because a sync would try to reach the network and fail.
cd "$ENV_PROJECT"

# A mismatch is a *verdict*, not a job failure: the runner exits 1 on one, and
# under `set -e` that would abort the script and mail a spurious FAIL. So the
# exit code is captured, and the job's own status is decided by whether a
# verdict artifact exists. "Job FAILED" then means exactly one thing --
# no comparison was produced -- which is what the poller and the email should
# both react to.
set +e
uv run --no-sync python3 -u -m mimic_utils.full_runner chemistry \
  --attempt-dir "$ATTEMPT_DIR" \
  --manifest "$ATTEMPT_DIR/oracle_manifest.full.json" \
  --no-color
RUNNER_RC=$?
set -e

echo "full run finished for chemistry (runner exit ${RUNNER_RC})"
ls -la "$ATTEMPT_DIR"

if [ ! -f "$ATTEMPT_DIR/comparison.full.json" ]; then
  echo "ERROR: no comparison.full.json produced — the run did not reach a verdict"
  exit "${RUNNER_RC:-1}"
fi
exit 0
