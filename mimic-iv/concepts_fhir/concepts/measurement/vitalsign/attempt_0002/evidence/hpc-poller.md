# HPC-poller evidence — vitalsign, attempt 0002

The full-data job completed successfully (Slurm job `30221058`, `hpc_accounting.json` elapsed 116 seconds, state `COMPLETED`). The fresh comparator artifact is `comparison.full.json`; this is a comparator verdict, not a queue failure.

Comparator verdict: `review`, schema match true, keyed diff on `(stay_id, charttime)`. Oracle rows: 9,745,500; candidate rows: 9,744,737; identical rows: 9,743,636 (99.9809%). Row count was reported, not gated.

Divergence: tier `contested`, `judge_required: true`, `diagnostician_required: true`. Classes are 1,106 `only_oracle`, 343 `only_candidate`, and 758 `differing_conflict` attributed completely by the comparator to `upstream_timestamptz_dst_shift`. Key replay attributed 343 candidate-only and 1,105 oracle-only rows (343 repaired, 762 collided), leaving one oracle-only residual; therefore the tier remains contested and requires diagnosis. The attributed conflict citation set is recorded in `comparison.full.json`, including `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`; the comparator also records the broader replay citation set.

Artifacts fetched:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
- remote `candidate.full.parquet` remains on scratch
