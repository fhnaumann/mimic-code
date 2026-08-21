# HPC poller evidence — icustay_hourly

Job `30309334` completed cleanly and produced a fetched full comparison; this
was a real comparator result, not a crash. Slurm elapsed time was 84 seconds.

The full schema matched: output columns were `stay_id`, `hr`, `endtime`, plus
required key columns `icu_encounter_key` and `patient_key`, with compatible
types and natural key `(stay_id, endtime)`. Row counts were oracle 7,799,814
and candidate 7,799,808 (delta -6), reported but not gated. Identical rows
were 7,799,747.

Comparator verdict: `review`, tier `contested`, `judge_required: true`,
`diagnostician_required: true`. The keyed diff contained 1 `only_candidate`,
60 `differing_conflict` rows (all on `hr`), and 7 `only_oracle` rows; no
null-only divergence or unrepresentable declaration. Conflict attribution was
not attempted because the target schema has no datetime value column. Key
attribution attempted a full `endtime` DST replay but was incomplete: 0/1
candidate-only and 0/7 oracle-only rows were attributed, leaving all eight
unpaired rows residual. The comparison cites the contested bar requiring an
upstream ETL citation and unrecoverability proof.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/icustay_hourly/attempt_0001/hpc_accounting.json`
