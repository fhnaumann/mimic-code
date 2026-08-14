# Evidence — equivalence-judge

Concept `nsaid`, attempt `0001`.

The independent judge read the comparison, attempt artifacts, canonical SQL,
source/FHIR analyses, loop contract, and curated MIMIC notes. It confirmed that
`MedicationRequest.dispenseRequest.validityPeriod.start/end` is absent for
invalid or incomplete intervals, that no Medication or ingredient element
preserves the original row-level timing, and that all defensible direct and mix
branches and identifier paths were tried. It confirmed the 18/235,678 conflicts
are fully attributable to `mimic-fhir/sql/fhir_medication_request.sql:43-44,172-176`
and rare DST-gap normalization. Because the missing clinically meaningful
timing is essential to this concept's output, the judge verdict is
`blocked`/`BLOCKED_REPRESENTATION`, not accepted divergence.

No files were written by the judge.
