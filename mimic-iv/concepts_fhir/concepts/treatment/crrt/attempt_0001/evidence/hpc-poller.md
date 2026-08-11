## Evidence

The submitted full-data job `29710188` completed normally after two polls;
Slurm accounting reports 101 seconds and no fatal markers. The fetched
comparison is a legitimate comparator result with verdict `review`, not a
crash.

The oracle has 287,152 rows and the candidate 287,089 (row count is reported,
not gated). The candidate reproduced 287,014/287,152 rows identically
(99.95%). The divergence is `contested` plus `gap_shaped`: 22
`only_candidate`, 53 `differing_conflict`, and 85 `only_oracle`. The conflict
columns include CRRT pressures/rates, categorical values and flags; the full
column details are in `comparison.full.json`. Because contested classes are
present, an upstream ETL diagnosis is required before convening the judge.

Fetched artifacts:

- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0001/hpc_accounting.json`
