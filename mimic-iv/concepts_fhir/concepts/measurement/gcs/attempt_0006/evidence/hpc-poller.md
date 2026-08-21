# HPC poller evidence — gcs attempt 0006

- Job `30310910` for attempt 0006 completed successfully; Slurm elapsed time
  was 148 seconds. No crash, timeout, OOM, or fatal marker occurred.
- The comparator verdict is `review`, with schema identity matching. Oracle row
  count is 1,637,763 and candidate row count is 1,637,739; row count is
  reported only and was not gated.
- The review tier is `gap_shaped`; `judge_required` is true and
  `diagnostician_required` is false. The 98 `only_oracle` and 74
  `only_candidate` key divergences were exhaustively attributed by the
  comparator to the upstream America/New_York `TIMESTAMPTZ` DST shift, with 24
  collided/absorbed rows and zero residual attribution rows.
- The remaining classified divergence is `differing_null_only`: declared
  all-null `gcs_unable` plus typed NULL `gcs`/`gcs_verbal` on 678,714 rows. The
  representable-column identical count is 958,951/1,637,763 (58.55%); total
  identical is 0 because the declared `gcs_unable` column is NULL throughout.
- Fresh artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and
  `hpc_accounting.json` in the attempt directory. No semantic decision or
  commit was made. Route directly to the equivalence judge because the
  comparator set `diagnostician_required: false`.
