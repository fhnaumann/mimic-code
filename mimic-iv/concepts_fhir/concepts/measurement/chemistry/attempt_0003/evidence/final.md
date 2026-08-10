Final evidence block — chemistry

- Terminal state: `COMPLETED_WITH_DIVERGENCE` (judge accepted); not an exact `match`.
- Converged attempt: `attempt_0003`.
- Full-data runs consumed: **2** (attempt_0002 and corrected attempt_0003); below the hard cap of 10.
- Final verdict: `review`, tier `contested`, accepted by the equivalence judge.
- Final comparison: schema matched; candidate/oracle rows 3,811,523/3,811,523; 3,811,325 identical (99.9948%); 198 `differing_conflict` rows, all `charttime`, exactly the intrinsic DST spring-forward transformation residual; zero `only_oracle`, `only_candidate`, and `differing_null_only` rows.
- Judge citation: `/Users/nau025/Documents/mimic-fhir/sql/fhir_observation_labevents.sql:15,121` casts and writes lab charttime through `TIMESTAMPTZ`; `fhir_specimen_lab.sql:9,18,58` stores the same transformed specimen MAX(charttime). The 02:xx→03:xx mapping is non-injective and unrecoverable by any FHIR query; no independent FHIR element preserves the original.
- Attempt artifacts: `ViewDefinition.*.json`, `concept.sql`, `candidate.demo.parquet`, `shape.demo.json`, `submit.slurm`, `hpc_job.json`, `comparison.full.json`, and `run_meta.full.json` under `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/` (full Parquet remains on scratch).
- Evidence files: `source-analyst.md` and `fhir-prober.md` under attempt_0001; implementation/demo/HPC/diagnosis/judge/final evidence under attempt_0002/0003 as applicable.
- `MIMIC_NOTES.d/chemistry.md` entries appended during this goal: lab `Specimen.type` display absent; Spark doubled-quote datetime pattern issue; do not coalesce FHIR dateTime strings with a Pathling instant before casting (plus its append-only correction). `MIMIC_NOTES.md` was never edited.
