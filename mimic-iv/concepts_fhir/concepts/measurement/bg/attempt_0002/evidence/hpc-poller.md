# HPC poll evidence

- Read: `hpc_job.json`, the completed remote job result, `comparison.full.json`, and `run_meta.full.json` for attempt 0002.
- Checked: job 29587320 completed successfully; the embedded Pathling/Spark execution produced 511,637 candidate rows with the expected 27-column schema and compatible types.
- Result: full-data comparator verdict `review`, tier `contested`, classification `unavailable_no_key`. Row counts match exactly (511,637 versus 511,637), with 148 `only_oracle` rows and 148 `only_candidate` rows. Because `bg` has no unique full-data key, the comparator cannot distinguish invented rows from NULL-for-value divergence; this must be diagnosed before judge review.
- Full-data runs consumed: 1 of the 10-run cap.
- Artifacts: `comparison.full.json`, `run_meta.full.json`.
- Shared knowledge read: `mimic-iv/concepts_fhir/MIMIC_NOTES.md`; no dataset-wide quirk was promoted by the mechanical poll stage.
