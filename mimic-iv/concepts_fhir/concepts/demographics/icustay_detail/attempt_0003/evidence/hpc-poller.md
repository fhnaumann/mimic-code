## Evidence

Polled job `29735525` for attempt 0003 with
`uv run mimic_utils hpc-poll icustay_detail`; outcome was `complete` and the
Slurm state was `COMPLETED`.

Comparator verdict: `review`, tier `contested`, with
`judge_required=true` and `diagnostician_required=true`. Schema identity
passed for all 18 columns. Oracle and candidate each contain 73,181 rows; the
row count was reported and not gated.

Keyed diff: 11,594 `differing_conflict` rows (race 11,501, admission_age 86,
icu_intime 10, los_icu 10, admittime 7, dischtime 1) and 61,587
`differing_null_only` rows for the declared-and-confirmed unrepresentable
`hospital_expire_flag`; no only-oracle or only-candidate rows. Representable
identical fraction was 61,587/73,181 (84.16%). DST replay attributed 2
admittime conflicts; 11,592 residual conflicts remain for diagnosis.

Fetched artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

All are under
`mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0003/`.
`candidate.full.parquet` remains on scratch per contract.
