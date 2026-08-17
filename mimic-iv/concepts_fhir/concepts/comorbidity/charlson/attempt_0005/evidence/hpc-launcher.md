## Full-data launch — `charlson` attempt 0005

Command run from the repository: `uv run mimic_utils hpc-launch charlson --attempt 5`.

1. Rendered `submit.slurm` successfully.
2. Staged the attempt and dependency files successfully to `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005`.
3. Login-node smoke test failed before submission. Warehouse, oracle, and staged manifest checks passed, then importing the staged runner failed:

```text
ModuleNotFoundError: No module named 'sqlglot'
```

The import chain was `full_runner.py` -> `embedded_runner.py` -> `export_mappings.py:62`. No `sbatch` was run, no job id exists, and `hpc_job.json` was not written. The launcher stopped as required; no substitute path or semantic diagnosis was attempted.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/submit.slurm`
- no `hpc_job.json` because no job was submitted

This is an HPC/environment failure, not a comparator verdict. No implementation artifact was changed and no commit was made.
