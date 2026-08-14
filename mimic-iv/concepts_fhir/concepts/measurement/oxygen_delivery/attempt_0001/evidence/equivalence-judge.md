## Evidence

The independent equivalence judge reviewed `LOOP_CONTRACT.md`, curated
`MIMIC_NOTES.md`, `comparison.full.json`, all attempt artifacts and evidence,
the canonical oxygen_delivery SQL, and the diagnostician's upstream ETL
citation. There are no divergent dependencies.

Verdict: `blocked`.

The full comparison had 601,509/601,546 identical rows, with 31
`only_candidate`, 34 `only_oracle`, and 3 `differing_conflict` rows. The
comparator's DST key replay paired 31 oracle/candidate rows, leaving three
collision rows and matched flow/device conflicts. Upstream
`mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts source charttime
through `TIMESTAMPTZ`; line 67 writes the transformed value to
`Observation.effectiveDateTime`. The original 02:xx DST-gap wall time is
unrecoverable; resource ids are opaque and `issued` is storetime.

This loss is essential because charttime controls the natural key, row
inclusion, window ranking, flow/device joining, grouping, and clinically
meaningful output values. The result is therefore not a faithful port despite
high representable fidelity. The judge recommended `BLOCKED_REPRESENTATION`.
