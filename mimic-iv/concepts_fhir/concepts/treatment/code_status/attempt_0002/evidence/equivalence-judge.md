# Equivalence judge evidence — code_status attempt 0002

The required equivalence judge assessed the `review` result (tier
`gap_shaped`, classification `unavailable_no_key`) and returned **`accept`**.

The missing representation is the hospital POE event selected by
`poe.order_type='General Care'` and `poe.order_subtype='Code status'`. No served
FHIR resource/path carries the event, `poe_detail.field_value`, or
`poe.ordertime`. The nearest candidate,
`MedicationRequest.identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/medication-request-poe').value`,
was tested and is a different medication/IV/TPN subset; its `authoredOn`,
`status`, and medication fields cannot substitute for code-status POE data.

The independently counted full-data POE/detail branch contains 197,931 rows,
matching the entire `only_oracle` residual. The candidate exactly reproduces
all 71,141 representable chart rows after attempt 0002's Observation.id UUID
witness recovery of the nine prior DST-normalized timestamps, leaving zero
`only_candidate` rows. Because the concept is unkeyed, formal
`identical_fraction` and `representable_fraction` are unavailable; diagnostic
representable-branch fidelity is 71,141/71,141 (100%), with overall oracle
coverage 71,141/269,072 (26.44%). No divergent dependencies exist.

The judge's dataset-wide POE absence finding was appended to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/code_status.md`. `MIMIC_NOTES.md` and
immutable attempt artifacts were not edited.
