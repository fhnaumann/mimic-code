# Evidence: equivalence-judge — chemistry attempt 0004

Independent verdict: **accept** for the `review` / `attributed` result.

The judge read `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, the canonical
chemistry SQL, current and prior chemistry attempt artifacts, the current
ViewDefinitions and full-run artifacts, state, and the cited upstream ETL
files. It did not read or cite any `MIMIC_NOTES.d` fragment and did not modify
files.

The comparator exhaustively replayed all 198 `charttime` conflicts as the
America/New_York spring-forward `TIMESTAMPTZ` normalization, with zero
residual. The port maps `Observation.effective.ofType(dateTime)` and the
upstream `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` casts and writes
that value. `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` independently
preserves the same normalized specimen timing. The original 02:xx wall time is
unrecoverable. The fraction 198/3,811,523 (~0.0052%) is consistent with rare
one-hour-per-year DST-gap wall times.

The judge confirmed 3,811,325/3,811,523 identical rows (99.9948%), zero
only-oracle, only-candidate, or null-only rows, no residual, and no excluded
columns. It confirmed the current SQL casts effective variants independently to
`TIMESTAMP_NTZ` before coalescing, and that resource keys are opaque equality
join/output identities only. There are no divergent dependencies. This proven
upstream DST defect is accepted under the contract and is not essential loss.

No new dataset-wide quirk was found; no notes fragment was modified.
