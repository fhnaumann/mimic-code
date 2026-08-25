# HPC-poller evidence — lods attempt_0001

Slurm job `30511719` completed normally. The full-data comparator returned
`match` on the keyed manifest key `stay_id`: all 73,181 of 73,181 oracle rows
were reproduced identically. Schema identity passed, with the three required
opaque key columns accepted as manifest-declared extras. All divergence
classes and per-column conflicts were zero; no judge or diagnostician was
required.

Row counts were oracle 73,181 and candidate 73,181 (delta 0), reported but not
used as a gate. The full artifacts are:

- `comparison.full.json` (`verdict: match`)
- `run_meta.full.json` (`engine: pathling-embedded`)
- `hpc_accounting.json` (Slurm elapsed 2,473 seconds)
- `hpc_job.json`

This was one full run total for the concept.
