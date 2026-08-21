## Diagnosis

**Root cause:** Almost all divergence is inherited upstream `TIMESTAMPTZ` normalization propagated through KDIGO dependency windows and the subject-level smoothing window. However, one non-DST `kdigo_uo` rounding discrepancy remains without an upstream ETL explanation, so the overall result is a **fixable bug**, not yet judge-ready.

The unkeyed counts are not evidence of invented rows.

### Attribution

Full-oracle replay found these normalized inputs:

- 145 `kdigo_creatinine` timestamps
- 393 `kdigo_uo` timestamps
- 26 retained CRRT timestamps
- 10 ICU `intime` values

Total: **574 moved inputs**.

Their propagation accounts for:

- **1,697 of 1,707 `only_oracle` tuples**
- **1,454 of 1,464 `only_candidate` tuples**

Mechanisms include the event-axis `UNION DISTINCT`, exact timestamp joins, dependency lookback windows, collisions at normalized 03:xx times, and `aki_stage_smoothed`’s subject-partitioned six-hour elapsed-time window. Another nine tuples per side had same-natural-key peers with every output within comparator tolerance.

The upstream transformations are:

- `mimic-fhir/sql/fhir_observation_outputevents.sql:9`, written at `:60`
- `mimic-fhir/sql/fhir_observation_labevents.sql:15`, written at `:121`
- `mimic-fhir/sql/fhir_observation_chartevents.sql:9`, written at `:67`
- `mimic-fhir/sql/fhir_encounter_icu.sql:31`, written at `:98`

Each casts a naive source wall time through `TIMESTAMPTZ` before serializing the FHIR datetime. The original 02:xx value is absent from the resulting `effectiveDateTime` or `period.start`; other timestamps are separate transformed source fields, and resource IDs are opaque. Therefore no FHIR query can recover the original wall time.

### Fixable residual

One tuple per side remains:

- stay `31463721`, charttime `2174-05-12 20:40`
- oracle `uo_rt_24hr = 0.0313`
- candidate `uo_rt_24hr = 0.0312`
- source inputs: urine output `70`, weight `84`, duration `26.666667`

The candidate result corresponds to dividing by the already rounded six-decimal duration (`0.0312499996 → 0.0312`), whereas the canonical calculation retains full internal duration precision before rounding (`0.03125 → 0.0313`). No cited ETL statement rewrites this value, so it must be treated as a **dependency implementation bug**.

**Recommended fix:** reopen/correct the completed `kdigo_uo` implementation so its rate calculation retains full duration precision internally and only casts the published `uo_tm_*` columns afterward. Then rerun `kdigo_stages` unchanged. The current target SQL correctly consumes `kdigo_uo` at `concept.sql:74` and preserves the canonical union, joins, and smoothing at `:87-102` and `:124-151`.

### Essentiality and routing

The normalized timestamps affect row inclusion, event grain, stage values, and temporal carry-forward. Nevertheless, proven DST damage is explicitly exempt from essential-loss blocking under `LOOP_CONTRACT.md`; it is an acknowledged upstream defect. The remaining rounding discrepancy is fixable rather than representational.

**Route:** retry only after fixing/reopening `kdigo_uo`; do not send this attempt directly to the judge. No `kdigo_stages` carryover stage is at fault: **invalidate none**.

## Evidence block

Concept `kdigo_stages`, attempt `0001`; tier `contested`; classification `unavailable_no_key`; comparator classes: 1,707 `only_oracle`, 1,464 `only_candidate`, with candidate execution and schema matching.

Read and checked `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the `concept-equivalence` skill, canonical `mimic-iv/concepts/organfailure/kdigo_stages.sql`, the oracle-manifest entry, both carryover analyses, all immutable attempt SQL/ViewDefinitions and full-run reports/evidence, and the cited `mimic-fhir/sql` statements. The curated datetime/DST, labevents-window, opaque-ID, and essential-loss entries explained the bulk divergence but not the final rounding residual.

Six diagnostic full-data probes were used to choose between affected ETL streams; DST-window closure versus a broad port defect; tolerance artifacts versus genuine conflicts; direct dependency effects versus smoothed propagation; DST collision rows versus unrelated values; and upstream transformation versus fixable arithmetic for the final residual. One metadata-only schema query and one non-executing quoting failure were additional setup. No attempt or comparator was rerun.

Root cause diagnosis: 574 upstream-normalized input timestamps explain 1,697 oracle and 1,454 candidate residual tuples after propagation; nine per side pair within tolerance; one tuple per side remains a fixable premature-duration-rounding bug in the inherited `kdigo_uo` implementation.

Classification: **fixable bug with separately proven upstream transformation loss**. Essentiality: no block recommendation—the DST portion is contract-exempt, and the residual is repairable. Recommended action: fix/reopen `kdigo_uo`, then rerun `kdigo_stages` without changing its SQL. Carryover stage at fault: **none**.

Appended provisional dataset-wide entry `Normalised dependency times propagate through relative-time stage windows` to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/kdigo_stages.md`.

No ViewDefinition, SQL, existing evidence, or commit was modified.
