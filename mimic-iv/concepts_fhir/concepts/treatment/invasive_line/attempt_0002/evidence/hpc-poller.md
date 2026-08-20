# HPC-poller evidence — invasive_line attempt_0002

- Slurm job `30237085` completed successfully; this was a complete poll
  outcome, not a crash or timeout. Full artifacts were fetched.
- Full comparator verdict: `review`, tier `contested`; schema matched and the
  row count was 93,378 versus 93,378 (reported only, not gated).
- The unkeyed full-tuple residual paired 664 rows on `(line_type, stay_id)`;
  92,714/93,378 rows were identical. The conflicts were `line_site` 657,
  `starttime` 7, and `endtime` 1. No gap-shaped classes or unpaired rows were
  reported.
- `divergence.judge_required` and `divergence.diagnostician_required` were
  both `true`. The comparator attributed only the seven `starttime` conflicts
  to its replayed upstream DST cast, leaving 657 residual conflicts for source
  diagnosis. No judge was convened at this stage.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
- Full candidate remains on the attempt's remote scratch path.
