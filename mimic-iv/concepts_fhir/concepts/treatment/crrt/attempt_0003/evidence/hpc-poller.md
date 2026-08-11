## Evidence

Attempt 0003 job `29714437` completed normally with Slurm state COMPLETED and
106 seconds elapsed. The full comparator returned `match` (exit code 0).

Oracle and candidate each contain 287,152 rows, with identical fraction
1.0000. The schema matches all 24 columns with no missing, extra, or
incompatible types. All divergence classes are zero: `only_oracle`,
`only_candidate`, `differing_null_only`, and `differing_conflict`. The
comparison is keyed on `(stay_id, charttime)` and requires no judge.

Fetched artifacts:

- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0003/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0003/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0003/hpc_accounting.json`
