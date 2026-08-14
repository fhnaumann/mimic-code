# Evidence: hpc-launcher

The current attempt passed staging and login-node smoke tests, then submitted the full-data Slurm job. The remote attempt is `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/oxygen_delivery/attempt_0002`; job id `29938370`; submission time `2026-08-13T23:11:11.523874+00:00`. Warehouse, oracle, staged manifest, and imports checks all passed.

Artifacts: `submit.slurm` and `hpc_job.json`. Polling was deferred to the sequential hpc-poller.
