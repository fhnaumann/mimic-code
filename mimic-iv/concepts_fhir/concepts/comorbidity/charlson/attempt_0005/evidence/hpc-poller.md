## Full-data poll — `charlson` attempt 0005

Polled job `30068637` from this concept's `hpc_job.json` at the mandated 300-second interval. Outcome was `crash`, not a comparator verdict: the job left the queue after 4 polls without producing `comparison.full.json`. Slurm accounting reports state `FAILED` and elapsed runtime 664 seconds.

The fetched Slurm log reports a Spark infrastructure failure during SparkContext initialization: repeated `NullPointerException` in `BlockManagerMasterEndpoint.register` while the executor heartbeater could not communicate with the driver, followed by transport quiet timeout and SparkContext initialization failure. The ViewDefinitions, candidate SQL, and comparator never ran.

Artifacts fetched:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/slurm-30068637.out`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0005/hpc_accounting.json`

Not produced:
- `comparison.full.json`
- `run_meta.full.json`

No row counts or semantic verdict exist. This was an HPC engineering failure, not a port mismatch or review.
