# HPC poller evidence

Job `29781171` completed normally; Slurm elapsed time was 93 seconds and the
fresh full-data artifacts were fetched. The comparator verdict was `review`,
tier `attributed`, with `diagnostician_required=false` and
117,898 oracle and candidate rows. There were 117,897 identical rows and one
`differing_conflict` on `charttime` at `specimen_id=20137346`; no
`only_oracle`, `only_candidate`, or `differing_null_only` rows. The comparator
replayed the single conflict completely to `upstream_timestamptz_dst_shift`
and cited `mimic-fhir/sql/fhir_encounter.sql:65` and
`mimic-fhir/sql/fhir_medication_request.sql:43-44`.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and
`hpc_accounting.json` in this attempt; the full candidate parquet remains on
scratch.
