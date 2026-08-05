#!/bin/bash
#SBATCH --job-name=mimic-full-oracle
#SBATCH --account=OD-221174
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=64
#SBATCH --mem=503g
#SBATCH --exclusive
#SBATCH --output=/scratch3/nau025/oracle/slurm-%j.out
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=Felix.Naumann@csiro.au

# Build the full MIMIC-IV 2.2 DuckDB oracle: raw hosp/icu tables, then the 65
# derived concepts. Output lands on /scratch3, which the login node reads
# directly -- there is no artifact fetch step.
#
# Prerequisites (login node, once):
#   export UV_CACHE_DIR=/scratch3/nau025/uv_cache
#   cd /scratch3/nau025/mimic-code
#   uv venv --python 3.12 .venv-oracle
#   uv pip install --python .venv-oracle duckdb==1.5.5
#
# Compute nodes have no internet, so the venv MUST already exist before sbatch.

set -euo pipefail

REPO=/scratch3/nau025/mimic-code
DATA=/scratch3/nau025/original-mimic-iv/mimic-iv-2.2
OUT=/scratch3/nau025/oracle

module load python/3.12.3

mkdir -p "$OUT"

# DuckDB spills large joins to temp_directory; the default would be a small
# node-local filesystem, so it is pinned to scratch explicitly.
export PYTHONPATH="$REPO/src"

"$REPO/.venv-oracle/bin/python" -m mimic_utils.build_full_oracle \
  --phase all \
  --data "$DATA" \
  --db "$OUT/mimic4-full.db" \
  --repo-root "$REPO" \
  --temp-dir "$OUT/duckdb_tmp" \
  --memory-limit 400GB \
  --threads 64

echo "oracle built: $OUT/mimic4-full.db"
ls -la "$OUT/mimic4-full.db"
