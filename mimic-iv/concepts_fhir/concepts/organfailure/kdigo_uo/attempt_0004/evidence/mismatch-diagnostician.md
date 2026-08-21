# Mismatch diagnostician evidence — kdigo_uo attempt 0004

## Diagnosis

The remaining 1,059 machine-unattributed conflicts are second-order consequences of irrecoverable upstream DST normalization, not a `kdigo_uo` SQL, dependency-join, weight-mapping, or precision defect.

`mimic-fhir/sql/fhir_observation_outputevents.sql:9` casts `outputevents.charttime` to `TIMESTAMPTZ`; line 60 writes only the normalized value to `Observation.effectiveDateTime`, and lines 62–65 preserve quantity but not the original wall time. The completed `urine_output` mapping reads that dateTime and groups by `(stay_id, charttime)`. For the weight effect, `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` applies the same cast to weight-event charttime; `weight_durations` derives interval boundaries with `LEAD(starttime)`, so a shifted boundary changes the half-open interval selection. Neither ETL emits the pre-cast charttime elsewhere. Resource UUIDs are opaque and were not inverted.

Full-source replay closed the divergence:

- 395 selected outputevents source rows moved, forming 393 `urine_output` groups across 391 stays.
- 157 moved to an unoccupied key, producing the 157 candidate-only partners.
- 236 moved onto existing 03:xx keys and were absorbed.
- Thus all 393 oracle-only rows, all 157 candidate-only rows, and the row delta of -236 are accounted for; comparator residual unpaired sets are zero.
- Through `kdigo_uo` lines 24–27, 54–92, and 102–134, the shift changes `LAG`, 6/12/24-hour `RANGE` windows, duration gates, rolling volumes, and rates. The half-open weight join at lines 141–144 can select a different interval when the weight boundary moves.
- The current comparison has 1,061 conflicts: 2 directly recognized by comparator collision replay and 1,059 second-order LAG/RANGE/join effects; source-side replay leaves zero unexplained rows.
- The lone `weight` conflict is inherited interval selection at stay `37523171`, where the shifted source boundary changes which weight is active at 03:00.
- Attempt 0004's six `DECIMAL(38,12)` → `DECIMAL(38,9)` changes removed the prior precision defect; no retry is recommended.

Classification: upstream transformation loss. It is not essential representation loss under the contract's explicit DST exception; route to the equivalence judge. No carryover invalidation is recommended.

## Evidence block

Concept: `kdigo_uo`; attempt: `0004`; tier: `contested`.

Schema matched. Oracle rows: `3,321,748`; candidate rows: `3,321,512`; identical: `3,320,294`. Divergence: 393 `only_oracle`, 157 `only_candidate`, 1,061 `differing_conflict`, zero `differing_null_only`. Conflict columns/counts: `uo_tm_6hr` 415, `uo_rt_6hr` 400, `uo_tm_12hr` 370, `uo_rt_12hr` 337, `uo_tm_24hr` 322, `urineoutput_6hr` 299, `uo_rt_24hr` 275, `urineoutput_12hr` 252, `urineoutput_24hr` 207, and `weight` 1. The source replay explains all divergence through the cited outputevents/chartevents `TIMESTAMPTZ` transforms and this concept's temporal SQL; no resource-id inversion was used.

Sources checked: canonical `kdigo_uo` SQL, canonical dependency SQL and completed dependency attempts, attempt 0004 SQL/ViewDefinition/full artifacts, attempt 0003 comparison/evidence, curated `MIMIC_NOTES.md`, and the cited `mimic-fhir` ETL files. Relevant provisional fragments were treated as leads and independently checked, not cited as evidence. No fragment entry was appended and no files were edited.
