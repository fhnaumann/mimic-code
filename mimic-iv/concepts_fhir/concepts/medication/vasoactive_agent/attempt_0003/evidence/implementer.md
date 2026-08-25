# Concept implementer evidence

Evidence block

Concept: `vasoactive_agent`; attempt: `0003`.

Files read before authoring:

- `mimic-iv/concepts_fhir/MIMIC_NOTES.md` (all 958 lines).
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/*.md`, including the owned
  `vasoactive_agent.md` fragment and the seven ICU medication fragments.
- `mimic-iv/concepts_fhir/carryover/vasoactive_agent/source-analyst.md`,
  `fhir-prober.md`, and `carryover.json`.
- Attempt 0002's byte-identical replay artifacts: both ViewDefinitions,
  `concept.sql`, `replay_provenance.json`, and the replay/demo evidence.
- `oracle/oracle_manifest.full.json`, including the `vasoactive_agent` entry.

Exact correction: `milrinone_rows` now joins the published `milrinone` dependency
on `m.icu_encounter_key = s.icu_encounter_key` and selects `s.stay_id`, matching
the other six vasoactive dependency patterns. The prior invalid `m.stay_id`
reference is absent. The canonical 14-boundary `UNION DISTINCT`, `LEAD` interval
construction, seven containment joins, final `t.endtime IS NOT NULL` filter, and
all seven rate columns are preserved.

The final SELECT follows the manifest order and explicitly casts `stay_id` to
`INTEGER`, `starttime`/`endtime` to `TIMESTAMP_NTZ`, and each rate column to
`FLOAT`. It appends the required opaque support keys `icu_encounter_key` and
`patient_key` verbatim. No identifier is obtained from a resource key, and no
resource-id inversion is used.

The two fresh ViewDefinitions preserve the verified MedicationAdministration
coding system plus all seven exact codes, both effective-time variants, ICU
Encounter identifier projection, Quantity fields, and opaque equality join
keys. No `unrepresentable.json` is needed for this parent interval concept.

Validation: `uv run mimic_utils lint-sql vasoactive_agent` was run against the
new current attempt and passed cleanly. The attempt was not demo-run or
full-run here; no state transition or commit was performed.

Applied established notes on identifier spines and opaque keys, polymorphic
effective fields, Quantity typing/precision, TIMESTAMP_NTZ datetime casting,
ICU Encounter identifier-system filtering, and omitted ICU inputevent
linkorderid. The owned fragment's four medication findings and the sibling ICU
medication fragments were read as provisional leads and were already verified
by the recorded vasoactive carryover probes; no fragment was appended.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0003/ViewDefinition.medication_administration.json`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0003/ViewDefinition.encounter_icu.json`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0003/concept.sql`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0003/evidence/implementer.md`
