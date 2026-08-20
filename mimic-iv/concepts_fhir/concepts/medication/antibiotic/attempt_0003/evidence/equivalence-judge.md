# Equivalence-judge evidence

Decision: `blocked` for attempt 0003; controller must enter
`BLOCKED_REPRESENTATION`.

The judge accepted the 70 prescription-time conflicts as intrinsic upstream
transformation loss: `mimic-fhir/sql/fhir_medication_request.sql:43-44`
casts endpoints through `TIMESTAMPTZ`, and `:172-177` writes the transformed
validity period. The 70/735,462 affected fraction (52 starttime, 23 stoptime)
is consistent with DST rarity; the 67 comparator-replayed conflicts plus the
three request-level duplicate-group alignment artifacts are non-blocking.

The judge found the separate invalid/incomplete-period loss essential. The
same ETL omits validity endpoints at `:172-177` unless complete and
non-reversed, leaving 43,453 `differing_null_only` rows: starttime NULL on
43,369, stoptime NULL on 43,422, and stay_id NULL on 13,494. `authoredOn` at
`:55,124` is pharmacy entertime, not an endpoint, and identifiers/references
at `:75,111-124` carry identity only. Missing starttime removes core timing
and the canonical half-open ICU assignment at
`mimic-iv/concepts/medication/antibiotic.sql:198-201`; no FHIR query can recover
it. This is not ancillary loss, so the result is not a faithful port.

All defensible direct/mix, multiplicity, medication-name, route, identifier,
Encounter.partOf, temporal, and `TIMESTAMP_NTZ` mappings were exhausted. The
implementation used opaque resource keys only for equality joins and did not
parse or regenerate ids. There are no divergent dependencies. Fidelity:
691,939/735,462 identical (94.0822%); no columns were declared excluded, so
representable fidelity is the same.

No new dataset-wide quirk was identified; the cited endpoint omission, DST
normalization, and essential-loss policy are already in `MIMIC_NOTES.md`. No
files were edited and no commit was made by the judge.
