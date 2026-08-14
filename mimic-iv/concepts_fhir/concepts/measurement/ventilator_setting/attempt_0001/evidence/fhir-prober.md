Evidence block — fhir-prober

The prober read AGENTS.md, fhir-mapping guidance, MIMIC_NOTES.md, all
MIMIC_NOTES.d fragments, the source analysis, and the canonical observation
ViewDefinition. It mapped ICU chartevents to Observation using the exact
system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`
and literal itemids. Patient and ICU Encounter references are equality joins
to identifier.value strings, cast to INTEGER for output; resource IDs remain
opaque. Effective dateTime is cast to TIMESTAMP_NTZ. Quantity value aliases
need numeric casts; text values use value.ofType(string).

Demo/source checks reported 14,831 target rows, exact itemid/system and
subject/stay/charttime/itemid multiset agreement, 14,408 Quantity values and
423 text values, complete patient/encounter joins, and numeric agreement after
FIO2/PEEP cleaning. The prober identified possible full-data DST-gap datetime
loss and categorical numeric Quantity-to-text loss, and appended dataset-wide
claims about Observation.issued population and absent CodeSystem resources to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/ventilator_setting.md`.

Reusable mapping was written and recorded at
`mimic-iv/concepts_fhir/carryover/ventilator_setting/fhir-prober.md`.
