## Authoritative Delta Condition.code uses proprietary ICD diagnosis systems
- Affected: `Condition.code.coding.system` and ICD-9/ICD-10 diagnosis discrimination
- Verified: `charlson` attempt_0001 embedded Pathling probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` found `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9` on 2,442/5,051 Conditions and `.../mimic-diagnosis-icd10` on 2,609/5,051; the hospital-linked subset was 2,193/4,506 and 2,313/4,506. No `http://hl7.org/fhir/sid/icd-9-cm`/`icd-10-cm` systems were served.

## Condition contains both hospital and ED diagnosis streams
- Affected: `Condition.encounter` and hospital diagnosis stream selection
- Verified: `charlson` attempt_0001 opaque-key join of `Condition.encounter.getReferenceKey(Encounter)` to `Encounter.getResourceKey()` found 5,051 Conditions: 4,506 linked to `identifier.system=.../encounter-hosp` across 275 encounters and 545 linked to `.../encounter-ed` across 221 encounters; all 5,051 had one coding, subject reference, and resolvable Encounter reference. `meta.profile` was the same `mimic-condition` profile for all 5,051, so it did not discriminate the streams.
