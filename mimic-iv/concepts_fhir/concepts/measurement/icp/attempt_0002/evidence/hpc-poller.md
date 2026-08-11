## Evidence

Job `29732606` completed normally and fetched the full comparison artifacts. `comparison.full.json` is an exact `match` with `divergence.tier: none`, no judge/diagnostician required, schema identity for `[subject_id, stay_id, charttime, icp]`, and keyed comparison on `[subject_id, charttime]`. All 173273 oracle rows reproduced identically; `only_oracle`, `only_candidate`, `differing_null_only`, and `differing_conflict` are all zero. Candidate and oracle row counts both report 173273, but count was not a gate. Slurm elapsed time was 81 seconds.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0002/`. This is the deciding full-data match; no judge was spawned.
