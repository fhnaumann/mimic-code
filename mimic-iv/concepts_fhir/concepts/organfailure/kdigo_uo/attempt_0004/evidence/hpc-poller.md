# HPC poller evidence — kdigo_uo attempt 0004

The existing Slurm job `30317129` was polled without relaunch. Outcome: `complete`; a fresh comparison artifact was fetched, so this is a comparator verdict rather than a crash or timeout.

- Schema identity: `match: true`; all expected columns/types present. `icu_encounter_key` and `patient_key` are required manifest key columns.
- Row count (informational): oracle `3,321,748`, candidate `3,321,512`, delta `-236`.
- Identical: `3,320,294` of `3,321,748` (`99.956%`).
- Comparator verdict: `review`.
- Divergence tier: `contested`.
- Classes: `1,061` `differing_conflict`; `393` `only_oracle` and `157` `only_candidate` were fully re-paired as upstream `TIMESTAMPTZ`/DST key attribution with zero residual; no gap-shaped or other unresolvable class.
- `divergence.judge_required: true`; `divergence.diagnostician_required: true` because `1,059` conflicts remain unexplained by the machine attribution.
- Slurm accounting: `205 s`, state `COMPLETED`.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0004/hpc_accounting.json`
