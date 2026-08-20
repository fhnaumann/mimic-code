Evidence block

Concept: `crrt`; attempt: `0007`; job `30237098`.

`uv run mimic_utils hpc-poll crrt` completed successfully and fetched the
write-once full artifacts. Slurm outcome: `complete`; Slurm state:
`COMPLETED`; elapsed: 104 seconds. The candidate executed through embedded
Pathling/Spark and the schema matched all 26 columns/types.

Comparator verdict: `review`, tier `attributed`. The diagnostician is not
required (`divergence.diagnostician_required=false`); the equivalence judge is
required (`divergence.judge_required=true`). Oracle rows: 287,152. Candidate
rows: 287,120 (reported, not gated). Identical rows: 287,078 (99.97%). The
remaining divergence is 26 `differing_conflict`, 48 `only_oracle`, and 16
`only_candidate` rows, all attributed completely by the comparator to the
upstream `America/New_York` DST spring-forward `TIMESTAMPTZ` transformation.
Conflict attribution and key attribution both have zero residual rows; 26
conflicts are collision rows and the key replay accounts for all unpaired rows.

The artifact citations include `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`
and the other upstream datetime ETL sites listed in `comparison.full.json`.
The judge must confirm provenance, rarity/fraction, and that the 32 collision
rows are consistent with this concept's own MAX pivot. UUID/resource-id
recovery was not used.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/treatment/crrt/attempt_0007/hpc_accounting.json`
