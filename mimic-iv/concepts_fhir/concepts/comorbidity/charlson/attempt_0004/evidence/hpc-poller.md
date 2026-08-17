# HPC poller evidence — charlson attempt 0004

Job `30065473` completed successfully after two polls; no crash or timeout markers were found. The fetched full comparison is `review`, tier `contested`, with `judge_required=true` and `diagnostician_required=true`. Schema matched. Candidate and oracle each had 431,231 rows, and row count was reported but not gated.

The only divergence was 61 `differing_conflict` rows (0.014%): `age_score` differed on 61 rows and `charlson_comorbidity_index` differed on the same 61 rows. There were no `only_oracle`, `only_candidate`, `differing_null_only`, or false-declaration findings. 431,170/431,231 rows were identical (identical fraction 0.999859). Sample conflicts were candidate age score exactly one greater than oracle, while all comorbidity flags matched. Conflict attribution was not attempted because this concept has no datetime column.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/comorbidity/charlson/attempt_0004/hpc_accounting.json`
