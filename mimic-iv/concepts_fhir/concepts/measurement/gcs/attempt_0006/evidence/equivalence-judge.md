# Equivalence judge evidence — gcs attempt 0006

- Read `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, the current and prior
  comparison artifacts and SQL, current ViewDefinitions and
  `unrepresentable.json`, and the current implementation/HPC evidence.
- Verdict: **blocked**.
- The intrinsic loss is the `No Response-ETT` discriminator. The upstream ETL
  at `mimic-fhir/sql/fhir_observation_chartevents.sql:69-80` writes numeric
  chartevents with `valuenum` as `Observation.valueQuantity` and does not carry
  source text, so `No Response` and `No Response-ETT` both arrive as Quantity 1.
- The loss is essential, not ancillary: canonical `gcs.sql:33-45,62-95,101-125`
  uses it for `gcs_verbal`, `gcs_unable`, total `gcs`, and immediate-previous
  six-hour carry-forward. Attempt 0006 therefore has typed NULL `gcs` and
  `gcs_verbal` on 678,714 rows and typed NULL `gcs_unable` on all rows; this
  cannot be published as a faithful core GCS table.
- Comparator facts checked: schema match; 1,637,763 oracle rows versus
  1,637,739 candidate rows (non-gating); 1,637,665 null-only differences;
  958,951/1,637,763 identical on representable columns (58.55%), and 0 total
  identical because of the declared column. The separate 98 only-oracle and 74
  only-candidate key rows were fully attributed to the upstream DST cast at
  `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`, with 24 collisions and
  zero residual; no resource-id reconstruction was used.
- No divergent dependencies and no new dataset-wide quirk were found. No notes
  fragment was appended.
