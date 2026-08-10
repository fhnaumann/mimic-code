## Final evidence

- Concept: `cardiac_marker`
- Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the equivalence judge
- Converged attempt: `attempt_0002`
- Full-data runs consumed: **1 of 10** (attempt 1 was rejected at the demo execution gate and consumed no HPC run)
- Full verdict: `review`, tier `contested`
- Schema: identical
- Row counts: oracle 295,246; candidate 295,246 (reported, not gated)
- Identical rows: 295,228/295,246 (99.9939%)
- Divergence: 18 `differing_conflict` rows, all `charttime`, candidate exactly one hour later; zero `only_oracle`, `only_candidate`, or `differing_null_only`

The judge accepted the divergence as irrecoverable DST-gap transformation loss. The cited upstream statements are `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` (TIMESTAMPTZ cast and effectiveDateTime write), `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` (same transformation on the alternate specimen path), and `fhir_observation_labevents.sql:16,122` (issued derives from storetime). The original 02:xx wall time cannot be recovered from FHIR without corrupting genuine 03:xx values.

Artifacts: `ViewDefinition.lab_observation.json`, `ViewDefinition.patient.json`, `ViewDefinition.encounter.json`, `ViewDefinition.specimen.json`, `concept.sql`, `shape.demo.json`, `candidate.demo.parquet/`, `submit.slurm`, `hpc_job.json`, `comparison.full.json`, `run_meta.full.json`, and stage evidence under `attempt_0002/`; attempt 1 remains immutable with its demo-failure evidence. One dataset-wide finding was appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/cardiac_marker.md`: filter itemid-derived Observation codes by exact string system/code before integer casts. No later note was appended.
