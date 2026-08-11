# HPC poller and full comparison evidence

Slurm job `29721166` for attempt 0003 completed successfully and fetched a fresh comparison. Full execution used embedded Pathling on Spark; schema matched exactly (`subject_id`, `hadm_id`, `arb`, `starttime`, `stoptime`) and row counts matched 39,534 versus 39,534. The unkeyed full-tuple comparison paired the residual 1:1 on anchored `(subject_id, hadm_id)`.

Comparator verdict: `review`, tier `contested`. It found 36,353 identical rows, 3,179 `differing_null_only` rows (candidate NULL validity values), and 2 `differing_conflict` rows (one `starttime`, one `stoptime`). The comparator attributed both conflicts to the upstream DST `TIMESTAMPTZ` transformation and cited `mimic-fhir/sql/fhir_encounter.sql:65` and `mimic-fhir/sql/fhir_medication_request.sql:43-44`; this requires diagnostician verification before convening the judge. Full-run artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/medication/arb/attempt_0003/`; `candidate.full.parquet` remains on scratch.

No dataset-wide quirk was newly discovered or appended; the existing notes cover omitted validity periods and DST-shifted FHIR datetimes.
