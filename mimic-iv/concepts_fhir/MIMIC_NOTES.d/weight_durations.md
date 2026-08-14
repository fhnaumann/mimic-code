## Chartevents Observation ETL applies global value and hard-coded-row omissions
- Affected: `Observation` resources generated from `mimiciv_icu.chartevents`, including any item-specific stream whose source SQL retains rows rejected by the ETL predicate.
- Verified: `weight_durations` fhir-prober read `mimic-fhir/sql/fhir_observation_chartevents.sql:34-38` and independently queried the authoritative demo Delta plus read-only DuckDB: the two target items had 570/570 non-NULL source `value` rows, the hard-coded tuple `(34934165, 2151-10-03 05:14:00)` had 0 source rows, and the target produced 570/570 FHIR Observations. The predicates are global to the chartevents ETL; the target-specific counts show they were unexercised here.

## ICU Encounter period endpoints are also DST-normalized through TIMESTAMPTZ
- Affected: `Encounter.period.start` and `Encounter.period.end` for ICU Encounters generated from `mimiciv_icu.icustays`.
- Verified: `weight_durations` attempt `0001` had 9 residual `starttime` conflicts where source `icustays.intime` was in the New York spring-forward gap; replay moved every `intime` from 02:xx to 03:xx and the canonical `intime - 2 hours` derivation moved from 00/01:xx to 01/02:xx accordingly. The upstream statements are `mimic-fhir/sql/fhir_encounter_icu.sql:31-32,97-100`; all 9 rows were independently checked against the full oracle and candidate after the comparator's direct value replay left them residual.

## ICU Encounter DST shifts can evade final-value replay after arithmetic
- Affected: arithmetic derived from `Encounter.period.start`, including first-admission weight `starttime` values.
- Verified: `weight_durations` attempt `0002` full-source replay found 9 of 70,688 selected ICU `intime` values shifted from 02:xx to 03:xx by `mimic-fhir/sql/fhir_encounter_icu.sql:31-32,97-100`; subtracting two hours moved the final conflicts outside the DST gap, producing exactly 9 residual `starttime` conflicts. The original ICU `intime` is not recoverable from the served period endpoint or opaque identity.
