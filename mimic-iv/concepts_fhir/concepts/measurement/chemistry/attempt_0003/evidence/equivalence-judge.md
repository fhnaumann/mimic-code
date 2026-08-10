Evidence block — concept: `chemistry`; attempt: `0003`; verdict: `accept`; tier: `contested`.

The contested bar was met. `mimic-fhir/sql/fhir_observation_labevents.sql:15` casts naive `labevents.charttime` through `TIMESTAMPTZ`, and line 121 writes the transformed value to `Observation.effectiveDateTime`; lines 16 and 122 preserve only `storetime` as `Observation.issued`. `fhir_specimen_lab.sql:9,18,58` stores the same transformed MAX(charttime) in `Specimen.collection.collectedDateTime`. The DST-gap mapping from 02:xx to 03:xx is non-injective and indistinguishable from genuine 03:xx values, so no FHIR query can reconstruct the oracle timestamp. Attempt 0003 applied the curated `TIMESTAMP_NTZ` workaround and both effective variants; no defensible mapping remains.

Acceptance justification: upstream MIMIC-on-FHIR ETL irreversibly normalizes DST spring-forward-gap laboratory charttimes through `TIMESTAMPTZ` before writing `Observation.effectiveDateTime`; no independent FHIR element preserves the original charttime. Accept 198 intrinsic `charttime` conflicts.

Fidelity: 198 `differing_conflict`, all in `charttime`; 0 `only_oracle`, 0 `only_candidate`, 0 `differing_null_only`; identical 3,811,325/3,811,523 = 99.9948%; representable fidelity 99.9948%, with no excluded or declared-unrepresentable columns. Divergent dependencies: none. Relevant curated notes: “FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ” and “DST-gap timestamps are irreversibly shifted +1 hour.” Retrying cannot recover information absent from FHIR.

No files were modified by the judge.
