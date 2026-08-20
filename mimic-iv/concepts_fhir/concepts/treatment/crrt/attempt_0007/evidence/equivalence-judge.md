Evidence block

Concept: `crrt`; attempt: `0007`; verdict: `accept`; tier: `attributed`.

The judge confirmed provenance: CRRT reads chartevents
`Observation.effectiveDateTime` (`ViewDefinition.crrt_observation.json:12`,
`concept.sql:26-28`), while `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`
casts source charttime through `TIMESTAMPTZ` and writes the normalized value.
The canonical query groups the original wall time.

The judge confirmed faithful collision behavior: repeated item `224146` rows
are preserved, and `concept.sql:42-93` applies the canonical per-column MAX
pivot over `(stay_id, charttime)`. The added resource key columns do not alter
the grain. No UUID/resource-id reconstruction was used; resource ids remained
opaque.

Full-data divergence accepted:
- 26 `differing_conflict`
- 48 `only_oracle`
- 16 `only_candidate`
- zero residual rows after exhaustive comparator attribution

Fidelity is 287,078/287,152 identical (99.9742%); the 26 conflicts are 0.0091%
of oracle rows and the 64 key-side findings are consistent with the rare
America/New_York DST-gap transformation. There are no dependencies and no
inherited divergence. The judge found no essential source loss or fixable
candidate defect.

Relevant curated evidence: `MIMIC_NOTES.md:423-475`, `:491-528`, `:203-230`,
and `:241-267`. No MIMIC_NOTES.d fragment was cited or modified.
