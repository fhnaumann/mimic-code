## ICU Encounter period endpoints are populated on the ICU stream
- Affected: `Encounter.period.start` and `Encounter.period.end` for `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`
- Verified: `sepsis3` attempt_0001 embedded Pathling 9.6.0/Spark 4.0.2 probe over `/Users/nau025/warehouses/mimic-iv-demo/delta` projected `period.start` and `period.end` and found 140/140 non-null ICU Encounters (the ICU stream had 140 rows); aliases materialized as strings.
