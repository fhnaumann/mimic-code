# Equivalence-judge evidence

Verdict: `accept` for the `contested` review.

The judge confirmed that `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` casts relational `labevents.charttime` through `TIMESTAMPTZ` and writes the normalized value to `Observation.effectiveDateTime`; attempt 0002 reads `Observation.effective.ofType(dateTime)` and preserves it with `TIMESTAMP_NTZ`. `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` applies the same loss to specimen timing. A normalized 03:xx is indistinguishable from a genuine 03:xx, and neither specimen timing nor opaque identifiers provides a recoverable pre-normalization wall-time witness.

The comparator directly replay-attributed 138 of 154 conflicts. The remaining 16 are second-order effects through the preserved strict 48-hour and seven-day windows: seven have shifted current charttimes and nine have unchanged current charttimes but shifted prior observations affecting ordering or boundary membership. The full result had 599,453/599,607 identical rows (99.9743%), with charttime conflicts 145, 48-hour minimum conflicts 12, and seven-day minimum conflicts 4; no missing, invented, or null-only rows. The contract's proven-DST exemption applies, including these downstream timing effects, so this is accepted rather than blocked.

Suggested controller justification: Accepted upstream DST transformation divergence. `mimic-fhir/sql/fhir_observation_labevents.sql:15,121` irreversibly casts `labevents.charttime` through `TIMESTAMPTZ` before writing `Observation.effectiveDateTime`; `fhir_specimen_lab.sql:9,18,58` repeats the transformation for specimen timing. Attempt 0002 reads that element and preserves the canonical 48-hour and seven-day windows. Of 599,607 rows, 599,453 are identical and 154 conflict (0.0257%): 138 replay directly and 16 are downstream ordering/window effects of shifted source observations. FHIR contains no independent pre-normalization wall-time witness, so exact chronology and membership are unrecoverable.

No artifacts were produced by the judge and no files were changed. No relevant sibling fragment was used; the concept fragment's attempt-0002 reconfirmation was not cited as judge evidence.
