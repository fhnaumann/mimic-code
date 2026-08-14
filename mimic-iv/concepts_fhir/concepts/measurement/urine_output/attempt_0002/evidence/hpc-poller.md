# HPC poller evidence

Concept: `urine_output`; attempt `0002`; Slurm job `29949872`.

Poll outcome: `complete`; job state COMPLETED, 62 seconds elapsed, artifacts fetched. Comparator verdict: `review`, tier `attributed`, with `judge_required=true` and `diagnostician_required=false`.

Schema matched exactly: `[stay_id, charttime, urineoutput]`, types `int`, `timestamp_ntz`, and `double`. Oracle rows: 3,321,748. Candidate rows: 3,321,512 (delta -236, reported but not gated). Identical rows: 3,321,123 (99.9812%). Key: `[stay_id, charttime]`.

Divergence: 232 `differing_conflict`, 393 `only_oracle`, and 157 `only_candidate`, all completely attributed to `upstream_timestamptz_dst_shift` in `America/New_York`, with zero residual. Of the unpaired oracle rows, 236 collided with existing candidate keys; these are absorbed rows and the other half of the same events, not separate port inventions. No gap-shaped, contested, unresolvable, blocking, declared-unrepresentable, or null-only classes.

Attribution citations now include the required outputevents writer: `mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65`, alongside the generic known sites. The judge must confirm provenance, DST-gap rarity, complete accounting of both unpaired sets, and no resource-ID reconstruction; no diagnostician is required.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0002/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0002/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0002/hpc_accounting.json`
- Candidate full Parquet remains on scratch per contract.
