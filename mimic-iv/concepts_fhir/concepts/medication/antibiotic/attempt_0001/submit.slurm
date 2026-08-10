#!/bin/bash
#SBATCH --job-name=port-antibiotic
#SBATCH --account=OD-221174
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=64
#SBATCH --mem=503g
#SBATCH --exclusive
#SBATCH --output=/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0001/slurm-%j.out
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=Felix.Naumann@csiro.au

# Full-data correctness run for one concept-port attempt.
#
# Template. `mimic_utils hpc-launch` renders the double-brace placeholders and
# rsyncs the rendered copy into the remote attempt directory; it is never
# submitted as-is. A rendered script therefore contains no braces at all, which
# is what `render_submit_script` asserts before anything reaches the queue.
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

REPO=/scratch3/nau025/mimic-code
ENV_PROJECT=/scratch3/nau025/mimic-on-fhir-delta
ATTEMPT_DIR=/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/antibiotic/attempt_0001

module load python/3.12.3 amazon-corretto/21.0.0.35.1

# The driver JVM is sized here, before Spark starts: PathlingContext cannot
# resize a heap that already exists. 400g of the node's 503g leaves headroom
# for the DuckDB comparison that runs in the same process afterwards.
export PYSPARK_SUBMIT_ARGS="--master local[64] \
  --conf spark.driver.memory=400g \
  --conf spark.driver.maxResultSize=32g \
  --conf spark.sql.shuffle.partitions=256 \
  --conf spark.default.parallelism=256 \
  pyspark-shell"

export MIMIC_FHIR_WAREHOUSE=/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse
export MIMIC_FULL_ORACLE=/scratch3/nau025/oracle/mimic4-full.db
export PYTHONPATH="$REPO/src"

# Run from the env project so `uv run` resolves its venv, but execute this
# repo's code via PYTHONPATH -- the same split the oracle build used.
# `--no-sync` because a sync would try to reach the network and fail.
cd "$ENV_PROJECT"

# A mismatch is a *verdict*, not a job failure: the runner exits 1 on one, and
# under `set -e` that would abort the script and mail a spurious FAIL. So the
# exit code is captured, and the job's own status is decided by whether a
# verdict artifact exists. "Job FAILED" then means exactly one thing --
# no comparison was produced -- which is what the poller and the email should
# both react to.
set +e
uv run --no-sync python3 -u -m mimic_utils.full_runner antibiotic \
  --attempt-dir "$ATTEMPT_DIR" \
  --manifest "$REPO/mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json" \
  --no-color
RUNNER_RC=$?
set -e

echo "full run finished for antibiotic (runner exit ${RUNNER_RC})"
ls -la "$ATTEMPT_DIR"

if [ ! -f "$ATTEMPT_DIR/comparison.full.json" ]; then
  echo "ERROR: no comparison.full.json produced — the run did not reach a verdict"
  exit "${RUNNER_RC:-1}"
fi
exit 0
