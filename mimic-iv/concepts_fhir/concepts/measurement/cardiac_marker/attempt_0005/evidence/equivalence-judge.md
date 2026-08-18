Evidence block

Concept: `cardiac_marker`; attempt `0005`; verdict: `accept`; tier: `attributed`.

Divergence: 18 `differing_conflict` rows on grouped `charttime`; zero `only_oracle`, `only_candidate`, or `differing_null_only` rows. All 18 replayed exactly through the `America/New_York` TIMESTAMPTZ round-trip, with zero residual. Fidelity was 295,228/295,246 identical rows (99.9939%); no columns were excluded as unrepresentable.

Provenance: `ViewDefinition.lab_observation.json:14` sources charttime from `Observation.effective.ofType(dateTime)`. Upstream `mimic-fhir/sql/fhir_observation_labevents.sql:15` casts `lab.charttime` to `TIMESTAMPTZ`, and line 121 writes that transformed value to `Observation.effectiveDateTime`. The specimen timestamp path is transformed identically at `mimic-fhir/sql/fhir_specimen_lab.sql:18,58`. The 18/295,246 fraction (approximately 0.00610%) and exhaustive +1-hour 02:xx-to-03:xx replay are consistent with rare DST spring-forward gaps.

Mapping exhaustion: attempt 0005 uses `TIMESTAMP_NTZ`, handles effective dateTime and Period-start variants, and reproduces specimen-level `MAX(charttime)` aggregation. No FHIR path retains the original wall time, and resource identity is opaque. Essentiality assessment: only the original wall-clock value is lost for 18 rows; row inclusion, specimen identifiers, analytes, and all other compared values are exact. Under the contract, proven upstream DST transformation loss is accepted, not blocked.

Divergent dependencies: none. Curated notes used: the datetime/TIMESTAMP_NTZ and labevents DST entries in `MIMIC_NOTES.md`; no fragment was cited.

Artifacts read: `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, canonical SQL, attempt 0005 comparison/SQL/ViewDefinitions/run metadata/shape/evidence, attempt history 0001-0004, carryover analyses, and upstream labevents/specimen ETL SQL.
