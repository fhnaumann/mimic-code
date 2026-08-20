# Equivalence-judge evidence

- Concept: `dopamine`; attempt: `0003`; verdict: `accept`; tier:
  `gap_shaped`.
- The judge found no populated ICU input-event/link-order identifier at
  `MedicationAdministration.identifier.value`. The upstream ETL selects no
  `linkorderid` and uses `orderid` only inside opaque UUID construction
  (`mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23`); the emitted
  resource has no identifier element (`:38-103`). Resource IDs cannot be
  inverted.
- This explains exactly 16,892 `differing_null_only` rows on `linkorderid`,
  with zero missing, candidate-only, or conflicting rows. Representable
  fidelity is 16,892/16,892 (100%); overall identity is 0% only because the
  declared column is NULL.
- All defensible mappings were exhausted: exact ICU code `221662`, ICU
  Encounter identifier recovery, both `effective[x]` variants, Quantity casts,
  and `TIMESTAMP_NTZ` parsing. Missing `linkorderid` affects neither row
  inclusion nor `(stay_id,starttime)` grain, grouping, carry-forward, or
  clinically meaningful rate, amount, and timing outputs. No divergent
  dependencies exist.
- Curated notes relevant to the ruling: opaque resource identity,
  polymorphic `effective[x]`, Quantity materialization, and `TIMESTAMP_NTZ`
  handling. No new notes fragment entry was required.
