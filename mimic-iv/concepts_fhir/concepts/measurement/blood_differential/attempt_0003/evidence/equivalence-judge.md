# Equivalence-judge evidence — blood_differential attempt 0003

The independent judge read the current comparison, run metadata, SQL,
ViewDefinitions, stage evidence, prior attempt comparison history, state
history, the contract, curated `MIMIC_NOTES.md`, and the upstream
`mimic-fhir/sql/fhir_observation_labevents.sql`. No diagnostician was needed
because the comparator set `diagnostician_required: false` for complete
attribution.

Verdict: **accept**. The judge confirmed that
`mimic-fhir/sql/fhir_observation_labevents.sql:15` casts naive
`labevents.charttime` through `TIMESTAMPTZ` and line 121 writes that transformed
value to `Observation.effectiveDateTime`; the original wall time is not
retained and `issued` is sourced separately. The candidate's
`(effective).ofType(dateTime)` plus `TIMESTAMP_NTZ` preserves the served FHIR
wall-clock value without introducing another conversion.

All 200 `charttime` conflicts replay under `America/New_York` with residual 0;
200/3,171,906 (0.0063%) is consistent with DST-gap rarity. There are no
only-oracle, only-candidate, or null-only rows. The judge explicitly ruled
that the proven upstream DST defect is transformation loss rather than
essential-loss blocking, even though `charttime` is aggregated with MAX by
specimen. Resource IDs remain opaque and are not used for recovery.

This is the judge's justification for acceptance as a divergence:

> All 200 divergences are `charttime` conflicts caused by irreversible upstream
> DST normalization. `mimic-fhir/sql/fhir_observation_labevents.sql:15` casts
> naive `labevents.charttime` through `TIMESTAMPTZ`, and line 121 writes the
> result to `Observation.effectiveDateTime`; no FHIR element retains the
> original wall time. The candidate sources `(effective).ofType(dateTime)` and
> casts it to `TIMESTAMP_NTZ`, faithfully preserving the served value. The
> comparator replayed every conflict through `America/New_York` with zero
> residual. The affected 200/3,171,906 rows (0.0063%) are consistent with
> DST-gap rarity. Resource IDs remain opaque and provide no permissible
> recovery path. Although `charttime` is output and aggregated with MAX by
> specimen, the proven upstream DST defect is expressly exempt from
> essential-loss blocking.

No new dataset-wide quirk was identified beyond the curated notes, so no notes
fragment was appended and `MIMIC_NOTES.md` was not edited.
