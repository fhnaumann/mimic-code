# Equivalence-judge evidence — creatinine_baseline attempt_0001

The independent judge reviewed the full comparator, attempt artifacts and
evidence, canonical `creatinine_baseline` and `age` SQL, LOOP_CONTRACT, curated
notes, dependency states, and the upstream ETL. It confirmed the contested
cause and returned **`blocked`**.

The upstream citation is
`/Users/nau025/Documents/mimic-fhir/sql/fhir_patient.sql:15,108`: the ETL
constructs and writes `Patient.birthDate` from `MIN(transfers.intime) -
anchor_age`, while canonical age uses `anchor_age` and `anchor_year`. No FHIR
element carries the exact anchor pair and resource ids are opaque, so the
oracle values are unrecoverable by a permissible query. The candidate age
mapping is the best defensible mapping, and the result is inherited entirely
from divergent dependency `age`; `chemistry` contributed no observed
divergence.

The judge found 460 age conflicts propagated to 460 `mdrd_est` conflicts and
85 clinically meaningful `scr_baseline` conflicts. Although row inclusion,
key, and grouping were unchanged, the missing exact age changes the core
baseline output, meeting the contract's essential-loss block. Fidelity was
430,771/431,231 identical (99.8933%), with no excluded/declarable columns and
no row gaps. No retry or carryover invalidation was warranted; no files were
changed by the judge.
