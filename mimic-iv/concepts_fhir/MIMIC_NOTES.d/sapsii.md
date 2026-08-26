## Served Delta Condition.code uses proprietary MIMIC diagnosis systems
- Affected: Condition.code.coding.system
- Verified: 2026-08-26 embedded Pathling probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` projected `forEach: "code.coding"`: 5,051 coding rows over 5,051 distinct Conditions (ratio 1.000), split 2,442 `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9` and 2,609 `.../mimic-diagnosis-icd10`; the hospital-Encounter-linked subset was 4,506 rows, split 2,193/2,313. Use the served systems, not the historical ICD URI claim in the curated notes.
