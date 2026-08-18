# hpc-poller evidence

Concept: `icp`; attempt: `0004`; job: `30109489`.

The full-data job completed after two polls with Slurm elapsed time 109 s;
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` were
fetched. Schema identity passed. The comparator returned `review`, tier
`attributed`, with `judge_required: true` and `diagnostician_required: false`.

Full keyed diff (key `(subject_id, charttime)`): oracle 173,273 rows versus
candidate 173,258 (row count is non-gating), with 173,252 identical rows, 4
`differing_conflict` rows on `icp`, 17 `only_oracle`, 2 `only_candidate`, and
zero `differing_null_only`. Conflict and key attribution replayed every one of
the 23 divergence rows to the upstream New York `TIMESTAMPTZ` DST shift, with
zero residual. The comparator's judge bar requires provenance of the cited ETL
statement, consistency with DST-gap rarity, and confirmation that the merged
MAX value follows the concept SQL; it explicitly forbids resource-id inversion.

Artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

all under `mimic-iv/concepts_fhir/concepts/measurement/icp/attempt_0004/`.
