HPC poll completed for `kdigo_uo`, attempt `0001`.

The poller followed recorded job `30309469` (two polls; no second launch), fetched valid write-once verdict artifacts, and reported outcome `complete`. Slurm state was `COMPLETED` with `elapsed_seconds: 200`.

The full comparator verdict is `review`, tier `contested`, with schema match, `diagnostician_required: true`, and `judge_required: true`. Oracle rows: 3,321,748; candidate rows: 3,321,512 (row count is reported, not gated); identical rows: 3,319,860 (99.94%). Divergences are 1,111 `differing_conflict` rows, 384 `differing_null_only` rows, 393 `only_oracle` rows and 157 `only_candidate` rows. The comparator fully attributes the two unpaired classes to the upstream `upstream_timestamptz_dst_shift` key replay, including 236 key collisions, but only 2 of 1,111 conflicts are attributed and 1,109 remain for diagnosis. The null-only gap is concentrated in `uo_rt_6hr` (47), `uo_rt_12hr` (125), and `uo_rt_24hr` (221).

Artifacts produced/fetched:
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_uo/attempt_0001/hpc_accounting.json`
