# Mismatch-diagnostician evidence

The diagnostician inspected the 22 residual conflicts rather than the 138 already replay-attributed rows. It found no port bug and no carryover stage to invalidate. Twenty-one residuals are downstream consequences of the same irreversible labevents timestamp transform: seven have a shifted current charttime and changed prior minimum, while fourteen have an unchanged current charttime but a shifted prior observation crossing a 48-hour or seven-day boundary. The remaining one is an ordinary `AVG` floating representation difference (`0.5` vs `0.49999999999999994`) within the comparator's declared tolerance.

The exact ETL citation is `mimic-fhir/sql/fhir_observation_labevents.sql:15,121`, which casts source `charttime` through `TIMESTAMPTZ` and writes it as `Observation.effectiveDateTime`; the parallel specimen path is `mimic-fhir/sql/fhir_specimen_lab.sql:18,58`. FHIR carries no original charttime witness that can distinguish a normalized 03:xx from a genuine 03:xx, so exact ordering and window membership are unrecoverable. No new attempt is required and no implementation artifact was changed.

The diagnostician appended and corrected the dataset-wide finding in `mimic-iv/concepts_fhir/MIMIC_NOTES.d/kdigo_creatinine.md`.
