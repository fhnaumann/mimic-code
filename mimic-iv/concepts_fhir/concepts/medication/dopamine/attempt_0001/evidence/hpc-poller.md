Evidence block — Concept: dopamine, attempt 0001.

Slurm job `29712980` completed cleanly and the poller fetched `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`. The full candidate and oracle each had 16,892 rows and identical schemas; row count was reported but not used as a gate. The comparator returned `review`, tier `gap_shaped`, with 16,892 `differing_null_only` rows on `linkorderid` (candidate NULL, oracle populated), zero `only_oracle`, zero `only_candidate`, zero `differing_conflict`, and zero blocking contradictions. The declared-and-confirmed unrepresentable column leaves 100% identical representable columns. This routes to the equivalence judge; it is not a mismatch.

Artifacts fetched: `mimic-iv/concepts_fhir/concepts/medication/dopamine/attempt_0001/comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
