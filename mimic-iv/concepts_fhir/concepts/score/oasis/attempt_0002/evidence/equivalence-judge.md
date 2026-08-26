# Equivalence-judge evidence

Concept: `oasis`; attempt: `0002`; comparator tier: `contested`.

The independent judge ruled **`blocked`**. Schema and row counts were exact
(73,181 candidate and oracle rows), with 73,127 identical rows and 54
`differing_conflict` rows (99.9262% identical/representable). The 54 residual
rows conflict only on `electivesurgery`, `electivesurgery_score`, `oasis`, and
`oasis_prob`: candidate elective 0 / score 6 versus oracle elective 1 / score
0. No other divergence class occurred.

The judge accepted the diagnostician's full source accounting: all 54 rows
are elective admissions with a non-surgical retained first service and a
later surgical service before ICU intime plus one day. The upstream loss is
cited to `mimic-fhir/sql/fhir_encounter.sql:45-57` (services ranked by
`transfertime`, row 1 retained), `:71,83-84` (only that service carried/joined),
and `:142-147` (one `Encounter.serviceType` coding written). Encounter
location is transfer careunit rather than service history at
`fhir_encounter.sql:7-26,69,171` and
`mimic-fhir/sql/fhir_location.sql:10-21,34`; no query over FHIR can recover the
omitted later service values/times and resource ids are opaque.

The judge found the loss essential: it changes the row-level elective flag,
the six-point OASIS component, total OASIS, and clinically meaningful
mortality probability (`mimic-iv/concepts/score/oasis.sql:91-97,197-199,255-275`).
Selective NULLs cannot isolate the affected rows. Divergent dependencies
`age` and `first_day_vitalsign` were considered and do not contribute to this
residual. The judge therefore required `BLOCKED_REPRESENTATION`, not
acceptance or another retry.

No files beyond this evidence artifact were modified by the judge.
