# Evidence: hpc-launcher — chemistry attempt 0004

`uv run mimic_utils hpc-launch chemistry` staged the immutable attempt and
submitted Slurm job `30104200` on Petrichor. The login-node smoke test passed
warehouse, oracle, staged-manifest, and import checks. The attempt-specific
remote staging path was
`/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0004`.

Artifacts written once:

- `submit.slurm`
- `hpc_job.json`

The state was `VALIDATING_FULL` with HPC counter 3 at launch. No polling was
performed in this stage, and no implementation artifacts or commits were
changed.
