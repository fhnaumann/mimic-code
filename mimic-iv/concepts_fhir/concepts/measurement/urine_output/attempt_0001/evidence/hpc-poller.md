# HPC poller evidence

Concept: `urine_output`; attempt `0001`; Slurm job `29949679`.

Poll outcome: `complete` (job state COMPLETED, 62 seconds elapsed); comparison artifacts fetched. This is separate from the comparator verdict, which is `review`, not `match` or `mismatch`.

Schema matched exactly: columns `stay_id`, `charttime`, `urineoutput`; types `int`, `timestamp_ntz`, and `double`. Full-data row counts were oracle 3,321,748 and candidate 3,321,512 (delta -236), reported but not gated. Identical rows: 3,321,123/3,321,748 (99.9812%).

The divergence tier is `attributed`, with `judge_required=true` and `diagnostician_required=false`. Classes: 232 `differing_conflict` on `urineoutput`, 393 `only_oracle` (236 collision/absorbed and 157 repaired), and 157 `only_candidate`; all were completely replayed to the upstream `upstream_timestamptz_dst_shift` in `America/New_York`, residual zero. There were no gap-shaped, contested, null-only, unresolvable, or blocking classes. The comparator cites upstream ETL datetime casts at `fhir_observation_chartevents.sql:9,67`, `fhir_observation_labevents.sql:15,121`, `fhir_specimen_lab.sql:18,58`, `fhir_encounter.sql:65`, `fhir_medication_request.sql:43-44`, and `fhir_medication_administration_icu.sql:8-9,61-69`. The judge must still confirm provenance for this output's source and that the affected fraction is consistent with DST-gap rarity; no diagnostician is required.

The comparator notes that 236 shifted rows collided into existing keys and that the aggregation consequence must be confirmed from the concept SQL; no resource-id reconstruction was used or recommended.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/hpc_accounting.json`
- Candidate full Parquet remains on scratch at `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/measurement/urine_output/attempt_0001/candidate.full.parquet/`.
