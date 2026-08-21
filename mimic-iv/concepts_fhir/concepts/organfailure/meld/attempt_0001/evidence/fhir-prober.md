# FHIR-prober evidence — meld

The prober read the curated MIMIC notes and provisional fragments, then checked
the authoritative demo Delta/Pathling representation. ICU `Encounter` is
selected by the exact `identifier.system` ending in
`identifier/encounter-icu`; the ICU encounter carries the `stay_id` identifier,
the patient reference, and `partOf` hospital Encounter reference. Hospital
Encounter identifiers provide `hadm_id`, and Patient identifiers provide
`subject_id`. The correct joins use type-prefixed resource/reference keys only
for equality; emitted MIMIC identifiers remain string `identifier.value` values
cast to the manifest integer types.

The checked demo had 140/140 ICU keys, patient references, parent hospital
references, ICU identifiers, hospital identifiers, and period endpoints. The
completed dependency views expose `first_day_lab` and `first_day_rrt` through
their published ICU encounter key and nullable numeric outputs; they must be
joined as dependency temp views, not rederived. No direct code set or new
dataset-wide quirk was found, so nothing was appended to
`MIMIC_NOTES.d/meld.md`.

Carryover produced: `mimic-iv/concepts_fhir/carryover/meld/fhir-prober.md`.
No attempt ViewDefinition or SQL was created by this stage.
