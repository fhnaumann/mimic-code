# HPC launcher evidence

Concept: `complete_blood_count`
Attempt: `attempt_0004` (replay/data rebuild)

The full-data attempt was staged at the per-attempt remote path and passed the
login-node smoke test. Slurm job `30484162` was submitted successfully. The
carried `concept.sql` and ViewDefinitions were not edited.

Artifacts:

- `submit.slurm`
- `hpc_job.json`

The next required action is polling this recorded job; no verdict is available
from launch alone.
