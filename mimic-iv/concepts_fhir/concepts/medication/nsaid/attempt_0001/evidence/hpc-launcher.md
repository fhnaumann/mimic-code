# Evidence — hpc-launcher

Concept `nsaid`, attempt `0001`.

`uv run mimic_utils validate-full nsaid` transitioned the concept to full
validation. `uv run mimic_utils hpc-launch nsaid` staged the attempt, passed the
warehouse/oracle/manifest/import smoke checks, and submitted Slurm job
`29910678` without modifying implementation artifacts.

Artifacts: `submit.slurm` and `hpc_job.json` in this attempt directory; the
remote attempt was staged under the per-attempt scratch path.
