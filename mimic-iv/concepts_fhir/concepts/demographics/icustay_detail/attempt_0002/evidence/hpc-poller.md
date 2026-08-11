## Evidence

Polled job `29734517` for corrected attempt 0002 with
`uv run mimic_utils hpc-poll icustay_detail`; no relaunch occurred.

Poll outcome: `complete`; comparator verdict: `review`, tier `contested`.
Schema identity passed for all 18 columns, keyed on `stay_id`. Oracle and
candidate both had 73,181 rows; row count was reported, not gated.

Diff classes: 11,606 `differing_conflict` rows and 61,575
`differing_null_only` rows, with no only-oracle or only-candidate rows. The
NULL-only class is the declared-and-confirmed unrepresentable
`hospital_expire_flag`; the declaration policy passed. Conflicting columns:
`race` 11,501, `admission_age` 86, `los_icu` 19, `icu_intime` 16,
`admittime` 10, `icu_outtime` 3, and `dischtime` 2.

DST replay attributed 2 of 11,606 conflicts; 11,604 remain unexplained, so
`divergence.judge_required=true` and
`divergence.diagnostician_required=true`, requiring diagnosis before the
judge. Representable identical fraction was 61,575/73,181 (84.14%).

Fetched artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

They are under
`mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0002/`.
`candidate.full.parquet` remains on scratch per contract.
