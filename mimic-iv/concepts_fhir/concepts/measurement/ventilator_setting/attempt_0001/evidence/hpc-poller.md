Evidence block — hpc-poller

Job `29952064` completed normally. `uv run mimic_utils hpc-poll ventilator_setting`
to an upstream DST cast.

Oracle rows: 1,006,127; candidate rows: 1,006,119; delta -8 (reported only).
The diff has 652,532 `differing_null_only` gaps, concentrated in
`ventilator_mode`, `ventilator_type`, and `ventilator_mode_hamilton`; 2
`differing_conflict`, 37 `only_oracle`, and 29 `only_candidate` findings were
all attributed to `upstream_timestamptz_dst_shift` on `charttime`, with zero
residual unpaired rows. Slurm elapsed time was 101 seconds.

The full artifacts are under the attempt directory:
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
