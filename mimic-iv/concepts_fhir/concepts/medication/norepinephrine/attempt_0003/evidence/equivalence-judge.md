# Equivalence-judge evidence — norepinephrine attempt_0003

The independent judge returned `accept` for the `review` / `contested` result.

The keyed diff is explicitly VOID DIFF because unrepresentable `linkorderid` is
part of manifest key `(linkorderid,starttime)`; its symmetric only-oracle and
only-candidate counts do not measure fidelity. The ICU ETL writes neither
`linkorderid` nor `MedicationAdministration.identifier`
(`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`), and its
opaque UUID cannot be inverted. The canonical query only projects linkorderid
(`mimic-iv/concepts/medication/norepinephrine.sql:4`); it does not use it for
inclusion, derivation, grouping, or aggregation, and all 336,000 event
occurrences/multiplicity are preserved. The judge therefore classified the
loss as ancillary rather than essential.

The judge also accepted the 58 unique timestamp residual rows (33 shifted
starts, 34 shifted ends, 9 both; 0.0173%) as irrecoverable upstream
transformation loss: source endpoints are cast through `TIMESTAMPTZ` at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9` and written to
Period start/end at `:61-66`. Attempt_0003's `TIMESTAMP_NTZ` mapping faithfully
preserves the served values. The corrected raw-rate mapping was verified: the
two full-data `mg/kg/min` rows both have `patientweight=1`, so the raw rate is
recoverable and correctly emitted.

Judge acceptance justification:

> The full comparison is VOID DIFF because unrepresentable `linkorderid` is
> part of manifest key `(linkorderid,starttime)`; its only-oracle/only-
> candidate findings do not measure fidelity. ICU
> `MedicationAdministration.identifier` is not written, and
> `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100` carries
> neither `linkorderid` nor another semantic field from which it can be
> recovered; line 20's UUID is opaque and may not be inverted. Canonical
> `norepinephrine.sql:4` only projects this administrative identifier, while
> all 336,000 source-event occurrences and their multiplicity are preserved,
> so the loss is ancillary. The remaining 58 timestamp rows are irreversibly
> normalized by the upstream `TIMESTAMPTZ` casts at
> `fhir_medication_administration_icu.sql:8-9` and Period writes at `:61-66`;
> candidate `TIMESTAMP_NTZ` faithfully preserves the served values. All
> defensible mappings were applied, including the corrected raw-rate mapping.

No new fragment section was needed: the concept-owned fragment already records
the ICU MedicationAdministration omission and its full-data confirmation.
