# Mismatch-diagnostician evidence

Concept: `oasis`; attempt: `0002`.

The diagnostician read the attempt-0002 comparison, immutable implementation,
canonical OASIS SQL, oracle manifest, curated notes, dependency interfaces,
and the owned fragment leads. It verified the residual against the full
oracle/source and upstream ETL.

The residual is exactly 54 `differing_conflict` rows and no other divergence:
73,127/73,181 rows are identical. All 54 are candidate
`electivesurgery=0`, `electivesurgery_score=6` versus oracle
`electivesurgery=1`, `electivesurgery_score=0`, with downstream OASIS total
and probability differing by the elective component. All 54 are genuinely
elective admissions whose retained first service is non-surgical but whose
later service before ICU intime + one day is surgical. They span 51
admissions; source-side accounting closed 54/54.

Priority is no longer a problem: `Encounter.priority` code `EL` is an exact
mapping for source `admission_type='ELECTIVE'` via
`mimic-fhir/sql/fhir_etl/map_encounter_priority.sql:14` and
`mimic-fhir/sql/fhir_encounter.sql:63-64,95-96,135-141`. The remaining loss
is upstream service-history truncation:

- `mimic-fhir/sql/fhir_encounter.sql:45-57` ranks `services` by
  `transfertime ASC` and retains only `row_num=1`;
- `fhir_encounter.sql:71,83-84` carries/joins that one service;
- `fhir_encounter.sql:142-147` writes one `Encounter.serviceType` coding.

No later service or `transfertime` is serialized. Encounter location is built
from transfers/careunits, not services, at
`fhir_encounter.sql:7-26,69,171` and `mimic-fhir/sql/fhir_location.sql:10-21,34`;
class, priority, type, period, and hospitalization fields carry no omitted
service history. Resource ids remain opaque. Therefore no query over served
FHIR can distinguish these source histories.

The loss is essential under the contract: it changes row-level elective
classification, a six-point component, total OASIS, and clinically meaningful
mortality probability. It cannot be isolated with selective NULLs without
also estimating/erasing otherwise exact rows. The judge-ready classification
is upstream transformation loss with an essential residual; recommendation to
the judge is `blocked`, not an implementer retry.

The controller reports divergent dependencies `age` and `first_day_vitalsign`;
the diagnostician checked that no residual OASIS columns from those inputs
differ and neither feeds the elective branch. No carryover invalidation or new
dataset-wide note was warranted. No implementation artifact, state, or commit
was changed.
