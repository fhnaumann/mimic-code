## Evidence

Polled already-submitted job `29732525` for `icustay_detail` with
`uv run mimic_utils hpc-poll icustay_detail`; it was not relaunched.

Poll outcome: `complete`; comparator verdict: `review`, tier `contested`.
`divergence.judge_required=true` and
`divergence.diagnostician_required=true`. Slurm completed normally with 24 s
elapsed.

Schema identity passed for all 18 columns: no missing, extra, or incompatible
types. Oracle and candidate row counts were both 73,181; this was reported,
not gated. Keyed diff: 59,690 identical rows (81.56%) and 13,491
`differing_conflict` rows (18.435%), with no `only_oracle`, `only_candidate`,
or `differing_null_only` rows. Conflicting columns were `race` (13,246),
`hospital_expire_flag` (187), `admission_age` (86), `icu_intime` (10),
`los_icu` (10), `admittime` (7), and `dischtime` (1).

The comparator attributed only 2 `admittime` rows to the known upstream
TIMESTAMPTZ DST shift (`mimic-fhir/sql/fhir_encounter.sql:65`, with the
medication-request citation also recorded); 13,489 conflicts remain
unexplained, so the tier remains `contested` and requires diagnosis before
the judge.

Fetched artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`

All are under
`mimic-iv/concepts_fhir/concepts/demographics/icustay_detail/attempt_0001/`.
`candidate.full.parquet` remains on scratch per contract.
