## Final evidence

- Concept: `blood_differential`
- Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the equivalence judge
- Converged attempt: `attempt_0002`
- Full-data runs consumed: **2** (attempt 0001 and corrected attempt 0002)
- Demo gates: both attempts passed shape validation; demo row counts were never gates
- Final full verdict: `review`, tier `contested`, accepted
- Final schema: exact 20-column identity
- Final keyed diff: 3,171,706 identical of 3,171,906 oracle rows; 200 `differing_conflict` rows on `charttime`; zero `only_candidate`, `only_oracle`, or `differing_null_only`
- Judge citation: `mimic-fhir/sql/fhir_observation_labevents.sql:15,121-122` irreversibly normalizes DST-gap 02:xx labevent charttimes to 03:xx through `TIMESTAMPTZ`; no FHIR query can recover the original wall time. The port's `TIMESTAMP_NTZ` preserves the served value.
- Artifacts: `comparison.full.json`, `run_meta.full.json`, `hpc_job.json`, demo shape/candidate Parquet, ViewDefinitions, `concept.sql`, and stage evidence under the attempt directories
- Notes fragment: appended one dataset-wide section to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/blood_differential.md` documenting synthesized Quantity values from source text when `valuenum` is NULL. `MIMIC_NOTES.md` was not edited.
