Evidence block — equivalence-judge

The judge ruled `blocked` for attempt 0001, tier `gap_shaped`. It found the
652,532 NULL-only differences intrinsic because
`mimic-fhir/sql/fhir_observation_chartevents.sql:69-80` writes
Observation.valueQuantity when valuenum is present and only writes
valueString when valuenum is NULL, while the source SQL needs chartevents.value
for ventilator_mode, ventilator_mode_hamilton, and ventilator_type
(`mimic-iv/concepts/measurement/ventilator_setting.sql:87-91`). The attempt's
best defensible mapping uses available valueString and typed NULL rather than
inventing a numeric-to-label codebook.

The judge separately accepted the comparator's complete DST attribution:
`fhir_observation_chartevents.sql:9,67` writes the shifted charttime to
Observation.effectiveDateTime; all 37 only_oracle, 29 only_candidate, and 2
conflict findings were explained, including 8 key collisions, at a rare
37/1,006,127 event fraction. Canonical and candidate MAX/grouping semantics
support the collision propagation, and IDs were used only for equality joins.

The categorical loss is essential, not ancillary: downstream
`mimic-iv/concepts/measurement/ventilation.sql:36,55-127,171-180` uses the
mode fields for clinically meaningful invasive/non-invasive classification and
temporal processing. Fidelity was 353,556/1,006,127 identical (35.14%), with
no declared-unrepresentable exclusion. The judge cited the curated MIMIC_NOTES
entries on essential loss, categorical chartevents, Quantity aliases, and DST.
No divergent dependencies and no new dataset-wide quirk were identified.
