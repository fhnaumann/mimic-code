# Equivalence-judge evidence — vitalsign, attempt 0002

Verdict: `blocked`.

The judge accepted the DST portion: `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` rewrites `charttime` into `Observation.effectiveDateTime`; all 758 conflicts were exhaustively replayed, and 758/9,745,500 (0.00778%) is consistent with DST-gap rarity. The candidate correctly propagates the served-data effect through its `GROUP BY`, `AVG`, and `MAX` operations. This portion is not essential loss under the mandatory DST exemption.

The judge blocked on the one residual oracle-only row: `(subject_id=13793458, stay_id=34934165, charttime=2151-10-03 05:14:00, glucose=96)`. The hard-coded/global predicate at `mimic-fhir/sql/fhir_observation_chartevents.sql:34-38` removes every source row at that tuple before FHIR Observation creation. Canonical grouping emits one clinically meaningful row from the duplicate `itemid=220621` source rows, but no FHIR query can restore its Observation, code, effective time, or value. This is essential semantic-grain/row-inclusion loss, not an ancillary NULL-able column; resource-ID recovery is forbidden.

Fidelity: 9,743,636/9,745,500 identical (99.9809%); representable fraction is likewise 99.9809%, with no excluded columns. There are no divergent dependencies. No new dataset-wide finding was reported.
