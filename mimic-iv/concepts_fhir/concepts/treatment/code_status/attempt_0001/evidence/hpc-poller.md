# HPC poller evidence — code_status attempt 0001

The submitted job `29680054` completed successfully. `comparison.full.json` and
`run_meta.full.json` were fetched for full-data run 1 of 10.

Comparator verdict: `review`, tier `contested`, classification
`unavailable_no_key`. Schema identity passed for all eight columns. Row counts
were oracle 269,072 and candidate 71,141 (delta -197,931); row count is not a
gate. The residual did not pair because the concept has no natural key.

Divergence reported:
- 197,940 `only_oracle` rows, gap-shaped and consistent with the absent POE
  code-status branch.
- 9 `only_candidate` rows, contested under the unkeyed comparison because
  invented rows and NULL divergence are indistinguishable.

The contested result requires diagnosis before convening the equivalence judge.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/run_meta.full.json`
