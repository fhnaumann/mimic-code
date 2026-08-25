# HPC poller evidence

## Concept and attempt

- Concept: `charlson`
- Attempt: `attempt_0007`
- Slurm job: `30485985`

## Result

- Job outcome: `complete` (`COMPLETED`).
- Full comparator verdict: `match`.
- Oracle rows reproduced identically: 431,231 / 431,231 (100.00%).
- Keyed diff: `identical=431231`, `differing=0`, `only_oracle=0`,
  `only_candidate=0`, `differing_conflict=0`, `differing_null_only=0`.
- Comparator tier: none; no judge or diagnostician was required.
- Schema matched; required FHIR key columns were present.
- Slurm elapsed runtime: 31 seconds.

## Artifacts

- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0007/hpc_accounting.json`
