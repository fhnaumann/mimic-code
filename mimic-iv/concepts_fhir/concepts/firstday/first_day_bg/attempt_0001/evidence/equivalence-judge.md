Evidence block — equivalence-judge

Verdict: `accept` for the `review`, tier `contested` result.

The contested bar is satisfied by upstream citations: `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` casts relational `labevents.charttime` through `TIMESTAMPTZ` and writes the normalized value to `Observation.effectiveDateTime`; `mimic-fhir/sql/fhir_specimen_lab.sql:18,58` applies the same lossy normalization to `Specimen.collection.collectedDateTime`; and `fhir_observation_labevents.sql:16,122` casts `storetime` to `Observation.issued`, which is not the original chart time. Resource IDs are opaque and cannot reconstruct it.

Six labevents for specimen `44663261` changed from `2151-03-14 02:02` to `03:02` and collapsed into one inherited `bg` row. For stay `33143532`, the canonical upper bound is `2151-03-14 02:30`, so the oracle includes the row and the candidate correctly excludes the served `03:02`. Removing that row reproduces all nine differing fields: five conflicts (`baseexcess_min`, `pco2_min`, `ph_max`, `po2_max`, `totalco2_min`) and four candidate-NULL calculations (`aado2_calc_min/max`, `pao2fio2ratio_min/max`). The 23:00 FiO2 is eligible at 02:02 but not at 03:02. No divergence remains unexplained.

The port faithfully preserves the completed dependency boundary, inclusive temporal window, grouping, and MIN/MAX aggregation. Expanding the window or subtracting an hour would corrupt genuine timestamps. The divergence is wholly inherited from judge-accepted dependency `bg` (`COMPLETED_WITH_DIVERGENCE`, attempt `0006`), with no independent first_day_bg loss or residual. Although it changes row inclusion and clinically meaningful aggregates, the contract explicitly exempts proven upstream DST corruption and its second-order effects from essential-loss blocking.

Magnitude: 1/73,181 output rows (0.00137%), six source labevents, one inherited `bg` row, and nine differing output fields; 73,180/73,181 identical (`0.999986`, 99.9986%). No unrepresentable exclusions. No `MIMIC_NOTES.d` fragment was read or cited by the judge; no new dataset-wide quirk beyond the curated DST rule was needed.

Artifacts read included `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, source SQL, cited ETL files, both carryovers and states, all attempt-0001 artifacts, and the completed `bg` attempt-0006 artifacts. No files were changed by the judge.
