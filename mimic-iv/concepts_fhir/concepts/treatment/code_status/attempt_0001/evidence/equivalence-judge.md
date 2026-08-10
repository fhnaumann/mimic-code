# Equivalence judge evidence — code_status attempt 0001

The equivalence judge assessed the required `review` result (tier
`contested`, classification `unavailable_no_key`) and returned **`bug`**.

The judge accepted that the missing code-status POE branch is an intrinsic
coverage gap: no served FHIR resource/path carries the selected
`poe_detail.field_value`, POE event time, or equivalent code-status payload;
the MedicationRequest POE stream is limited to medication/IV/TPN orders. That
explains the 197,931-row branch deficit.

The judge rejected acceptance of the nine timestamp substitutions because an
exact recovery route was not attempted. Upstream
`mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` normalizes naive
`charttime` through `TIMESTAMPTZ` before writing `Observation.effectiveDateTime`,
but lines `21,41,45`, with namespace construction at
`mimic-fhir/sql/fhir_etl/uuid_namespace.sql:27`, preserve the original
`stay_id-charttime-itemid-value` as the UUIDv5 Observation ID. The FHIR-carried
resource ID can therefore be used as an equality witness to recover the
original 02:xx timestamp without corrupting genuine 03:xx rows. The judge
required a new attempt applying that mapping.

Verdict: `bug`; no controller terminal transition was made and no judge
acceptance was recorded. No divergent dependencies exist. Diagnostic chart
fidelity was 71,132/71,141, while formal identical/representable fractions
were unavailable because the unkeyed residual did not pair.

The judge's dataset-wide finding was appended to the owned fragment as
“Chartevents Observation.id preserves the pre-normalization charttime input”.
`MIMIC_NOTES.md` and immutable attempt artifacts were not edited.
