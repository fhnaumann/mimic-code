# FHIR-prober evidence — creatinine_baseline attempt_0001

The prober read the canonical source analysis, curated `MIMIC_NOTES.md`,
relevant provisional fragments, dependency analyses, the LOOP_CONTRACT, and
the MIMIC-on-FHIR ViewDefinition conventions. Embedded Pathling/Spark probes
over the authoritative demo Delta confirmed creatinine item `50912` under the
MIMIC lab-item system (3,003 rows), Quantity values on all target rows,
hospital Encounter references on 2,366/3,003 rows, and Condition ICD-9/10
systems and prefixes after filtering to the hospital Encounter identifier.
Condition data mixed hospital and ED streams and required the opaque
Condition-to-Encounter equality join plus `encounter-hosp` filtering.

The prober also confirmed a seven-column, `hadm_id`-keyed reconstruction on
275 demo admissions, with the known Patient.birthDate-derived age limitation
inherited from `age`; the single demo DST-shifted creatinine chart time is
ancillary because this concept groups only by admission/specimen and does not
use time. Quantity aliases are string-like and require numeric casts; FHIR
datetimes require `TIMESTAMP_NTZ`. Reusable mapping was written and recorded
at `carryover/creatinine_baseline/fhir-prober.md`.

The prober appended the dataset-wide provisional finding in
`MIMIC_NOTES.d/creatinine_baseline.md` documenting the served MIMIC diagnosis
systems and hospital/ED Condition mixing. `MIMIC_NOTES.md` was not edited.
