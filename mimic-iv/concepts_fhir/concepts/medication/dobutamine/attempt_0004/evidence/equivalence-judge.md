## Evidence

- Concept: dobutamine
- Attempt: attempt_0004 (replay/data rebuild)
- Stage: equivalence-judge
- Inputs checked: `LOOP_CONTRACT.md`, curated `MIMIC_NOTES.md`, current state/history, prior attempt evidence/comparisons, `comparison.full.json`, `unrepresentable.json`, carried SQL/ViewDefinitions, and carryover analyses.
- Comparator result: `review`, `gap_shaped`; `differing_null_only=8513` on declared `linkorderid`; `only_oracle=0`, `only_candidate=0`, `differing_conflict=0`; representable fidelity 8513/8513 (100%).
- Verdict: `accept`.
- Cited reason: ICU `MedicationAdministration` exposes no `inputevents.linkorderid` at `identifier.value`, `supportingInformation`, or another served path. The exhaustive ETL projection is `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`; `orderid` appears only in the opaque UUID construction at line 20. Resource-ID inversion is forbidden. The declared administrative identifier gap explains exactly all 8513 null-only rows, while stay/time alignment and rate, amount, and endpoints remain exact within comparator tolerance. The loss is ancillary and does not alter inclusion, grain, grouping, temporal carry-forward, or clinical outputs.
- Replay context: the byte-identical port ran against the rebuilt UTC warehouse; the prior DST row/key divergence disappeared, leaving only the linkorderid gap.
