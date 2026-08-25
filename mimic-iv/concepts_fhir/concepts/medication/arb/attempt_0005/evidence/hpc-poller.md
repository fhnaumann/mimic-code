# HPC poller evidence — arb attempt 0005

Job `30483917` completed successfully and fresh full-data artifacts were
fetched. The deterministic comparator returned `review`, not `match` or
`mismatch`, with tier `gap_shaped`, classification `paired_residual`,
`judge_required: true`, and `diagnostician_required: false`. Schema matched;
the 39,534-row candidate and oracle counts matched (row count is not a gate),
with 36,355 identical rows. The residual was 3,179
`differing_null_only` rows: candidate `starttime` was NULL for 3,179 rows and
candidate `stoptime` was NULL for 3,178 rows; there were no conflicts and no
only-candidate or only-oracle rows.

Artifacts fetched:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

The result requires the equivalence judge. No dataset-wide quirk was newly
discovered by the mechanical poll.
