# HPC poller evidence — code_status attempt 0002

Job `29681874` completed and its comparison artifacts were fetched. This was
full-data run 2 of the hard cap of 10.

Verdict: `review`, tier `gap_shaped`, classification
`unavailable_no_key`. Schema identity passed for all eight columns. Row counts
were oracle 269,072 and candidate 71,141 (delta -197,931); row count is not a
gate. The only divergence was 197,931 `only_oracle` rows. There were zero
`only_candidate` rows and no value conflicts after the UUID-witnessed timestamp
correction. The unkeyed residual did not pair, so the judge has reduced
evidence, as required by the comparator.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/run_meta.full.json`
