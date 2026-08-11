## Evidence

Attempt 0002 job `29713006` completed normally; Slurm elapsed time was 107
seconds and two polls were required. The fetched comparator is `review`, not a
crash or mismatch. Oracle rows: 287,152; candidate rows: 287,121 (reported,
not gated). Identical rows: 287,088/287,152 (99.98%).

Divergence is tier `contested`: 6 `only_candidate`, 27
`differing_conflict`, and 37 `only_oracle`; there are no
`differing_null_only` rows or unrepresentable declarations. Conflicts affect
20 output columns, with the largest counts on filter/return/effluent/access
pressure (19, 19, 18, 17). The comparator artifact explicitly requires a
diagnosis before the judge because contested classes are present.

Fetched artifacts:

- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0002/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0002/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0002/hpc_accounting.json`
