# Evidence — equivalence-judge

Concept `nsaid`, attempt `0002`.

The independent judge read the current comparison, all attempt artifacts and
history, canonical SQL, carryover analyses, and curated `MIMIC_NOTES.md`. It
verified the `gap_shaped` paired-residual result: 10,276
`differing_null_only` rows (`starttime` null on 10,276 and `stoptime` null on
10,249), plus 18 fully attributed DST conflicts (`starttime` 12,
`stoptime` 6), with no residual candidate-only or oracle-only rows. Fidelity
was 225,384/235,678 identical (95.63%). No dependency divergence was inherited.

The judge confirmed that `MedicationRequest.dispenseRequest.validityPeriod.start`
and `.end` are absent for invalid or incomplete intervals because
`mimic-fhir/sql/fhir_medication_request.sql:172-177` writes them only for a
complete valid period; `authoredOn` is not an alternative. The current port
tried both validity paths, direct and mix branches, and opaque resource-key
joins. Because canonical `nsaid.sql:30-35` emits the prescription start and
stop times, the missing clinically meaningful timing is essential. The judge
verdict is `blocked` / `BLOCKED_REPRESENTATION`.

The separate 18 conflicts were accepted as an upstream DST transformation, not
the block: `mimic-fhir/sql/fhir_medication_request.sql:43-44,172-177` writes
the sourced endpoints, the comparator replayed all 18, and 18/235,678
(0.0076%) is consistent with DST-gap rarity.

No new dataset-wide quirk was found and no notes fragment was appended. No
files were written by the judge beyond this orchestrator-stored evidence.
