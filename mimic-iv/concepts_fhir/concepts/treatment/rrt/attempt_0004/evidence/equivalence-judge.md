## Equivalence judge — concept `rrt`, attempt 0004

**Verdict:** `accept`  
**Tier:** `contested`

The unkeyed `full_tuple_multiset` comparison had 449 `only_oracle` entries (0.01588% of 2,827,715), 241 `only_candidate` entries (0.00852%), and row delta -208. The full-oracle raw-timestamp replay exactly reproduced all 2,827,715 oracle rows. Applying upstream New York `TIMESTAMPTZ` normalization exactly reproduced all 2,827,507 candidate rows, including every divergence entry, leaving zero residual.

Of 4,104,373 selected source rows, 635 were affected: 608/4,004,998 chartevents (0.01518%), 27/85,372 inputevent intervals (0.03163%), and 0/14,003 procedureevents. The overall affected source fraction, 0.01547%, is consistent with a rare one-hour annual DST gap rather than a broadly applied port error.

ETL provenance:
- `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` casts source `charttime` through `TIMESTAMPTZ` and writes it to `Observation.effectiveDateTime`.
- `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69` casts and writes input interval endpoints.
- `mimic-fhir/sql/fhir_procedure_icu.sql:10-11,73-75` performs the analogous rewrite, with zero selected RRT procedure endpoints shifted.

The original 02:xx wall times are absent from semantic FHIR paths. `Observation.issued` is source store time, not chart time. Resource IDs were not parsed, regenerated, hashed, hardcoded, or used to infer timestamps; they were used only for identity joins/provenance, consistent with `MIMIC_NOTES.md:203-230`.

Second-order propagation is expected: canonical `mimic-iv/concepts/treatment/rrt.sql:260,296-313` uses `UNION DISTINCT`, while `:316-326` applies the inclusive interval overlay and `COALESCE`. Attempt 0004 preserves those constructs at `concept.sql:57-120,121-135`, so shifted source records can collide, gain or lose interval partners, change multiplicity, and change dialysis values.

The earlier missing code `225965` is present in the current attempt. No selected input row had `rate IS NULL`, no selected procedure row was lost through `value IS NULL`, and no carryover stage is implicated. The unkeyed source-side replay is weaker than keyed comparator attribution, but it closes both complete multisets with zero residual. The judge therefore accepted the proven upstream DST defect under `LOOP_CONTRACT.md:256-315`; despite changing RRT inclusion, multiplicity, timing, and status, it is not essential loss and requires no retry or block.

No new dataset-wide quirk was found and no fragment was appended.
