# HPC-launcher evidence

The full-data attempt was staged and submitted successfully through `uv run mimic_utils hpc-launch milrinone`. Remote attempt: `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/medication/milrinone/attempt_0001`. Login-node smoke checks passed for warehouse, oracle, staged manifest, and imports. Slurm job `29883658` was submitted under account `OD-221174`.

Artifacts created: `submit.slurm` and write-once `hpc_job.json` under the current attempt. No full comparison was available at launch; polling is required.
