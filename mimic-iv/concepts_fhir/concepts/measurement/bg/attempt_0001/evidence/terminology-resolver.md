# Terminology-resolver evidence — bg

**Verdict:** terminology translation is not applicable. `bg` uses proprietary,
flat numeric item filtering; production should filter exact system + code and
must not invoke `$translate`.

**Systems/codes checked:**

- `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`: 52033,
  50801–50806, 50808–50811, 50813–50825; 50807 is dead in the demo.
- `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`:
  220277 (SpO2) and 223835 (FiO2).

Velonto queries on 2026-08-07 found no ConceptMap for either served source
system. The available MIMIC observation map uses a different source URI and
does not contain these codes. `$translate` for representative 220277 and
50821 returned no mapping, which is unresolved rather than explicit
`unmatched`. CodeSystem lookups confirmed displays for 50821 (`pO2`) and 220277
(`O2 saturation pulseoxymetry`), but no output column carries a code.

**Reproducibility:** the relevant ConceptMap was preflighted at version 1.0.0,
date 2026-08-05, SHA256
`11332d7e098937fc07325ebc105c56b03fef3c145ecd0fc504368aefaa9273c4`; its full
FHIR JSON snapshot is
`mimic-observation-merged-to-standard.fhir.json`. The attempt ledger is
`terminology_hashes.json`. The flat CodeSystems were queried for version
1.4.1-csiro but are not used in production and were not snapshotted.

**Dataset-wide finding promoted:** added the note that no ConceptMap covers the
served lab/chart Observation systems; future ports must filter proprietary
codes rather than translate them.

**Artifacts:**

- `mimic-iv/concepts_fhir/carryover/bg/terminology-resolver.md`
- `mimic-iv/concepts_fhir/carryover/bg/carryover.json`
- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0001/mimic-observation-merged-to-standard.fhir.json`
- `mimic-iv/concepts_fhir/concepts/measurement/bg/attempt_0001/terminology_hashes.json`
- updated `mimic-iv/concepts_fhir/MIMIC_NOTES.md`
