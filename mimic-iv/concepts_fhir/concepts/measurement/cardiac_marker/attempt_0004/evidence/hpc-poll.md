# Evidence: hpc-poll

Concept: `cardiac_marker`; attempt `0004`; Slurm job `29720149`.

The poll outcome was `complete`; the embedded Pathling/Spark full run executed
and the comparison artifacts were fetched. The comparator returned `review`,
tier `contested`, with schema identity and equal row counts (295,246 candidate
and oracle). There were 295,228 identical rows and 18
`differing_conflict` rows, all on `charttime`; no `only_oracle`,
`only_candidate`, or `differing_null_only` rows occurred. Samples show the
candidate exactly one hour later than the oracle, consistent with a DST-gap
rewrite. Slurm elapsed time was 104 seconds.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
