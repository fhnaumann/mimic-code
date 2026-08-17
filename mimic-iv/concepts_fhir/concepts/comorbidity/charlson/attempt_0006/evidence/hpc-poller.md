## Full-data poll — `charlson` attempt 0006

Job `30069960` completed normally after 2 polls. Outcome was `complete`, with comparator verdict `review` at tier `contested`; these are distinct. Slurm state was `COMPLETED`, elapsed runtime 33 seconds.

Comparison summary:
- Schema matched: all 21 expected columns plus the declared `patient_key` and `encounter_key` key columns; no missing or incompatible columns.
- Candidate and oracle row counts were both 431,231 (reported, not gated).
- Keyed diff used `hadm_id`; 431,170/431,231 rows were identical (99.9859%).
- Divergence: `differing_conflict` 61; `only_oracle`, `only_candidate`, and `differing_null_only` all 0.
- Conflicting columns were `age_score` (61) and `charlson_comorbidity_index` (61), with all individual comorbidity flags matching.
- `divergence.judge_required: true`; `divergence.diagnostician_required: true`; attribution was not attempted because this concept has no datetime column.

Artifacts fetched:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0006/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0006/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0006/hpc_accounting.json`

This is a semantic `review`, not a mismatch or infrastructure failure. It requires diagnosis before the judge under the contested-tier contract.
