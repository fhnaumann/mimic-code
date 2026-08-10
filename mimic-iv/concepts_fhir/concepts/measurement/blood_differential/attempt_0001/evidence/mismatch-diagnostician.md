## Evidence

The diagnosis read `comparison.full.json`, `run_meta.full.json`, all attempt artifacts, source and FHIR carryover, `LOOP_CONTRACT.md`, curated notes, and the notes protocol.

The divergence is mixed. The 200 `differing_conflict` rows are all `charttime` and exactly +1 hour on the candidate for March Sunday 02:xx values. The upstream ETL casts `lab.charttime` through `TIMESTAMPTZ` at `mimic-fhir/sql/fhir_observation_labevents.sql:15` and writes the resulting value at line 121. The original wall time is not retained in FHIR; `issued` is sourced separately from `storetime`, so no FHIR query can recover it. The existing curated DST note covers this, and the implementation's `TIMESTAMP_NTZ` handling is correct.

The five `only_candidate` rows are a fixable bug. They are specimen IDs `21438597`, `27736375`, `34063806`, `55540346`, and `72269481`, all itemid `51301` source rows with `value='<0.1'` and `valuenum=NULL`. The FHIR ETL synthesizes a numeric Quantity and comparator from text at `mimic-fhir/sql/fhir_observation_labevents.sql:27-47`, then writes it at lines 123-132. The port accepted every non-null Quantity and therefore violated source `valuenum IS NOT NULL`; it should project Quantity comparator and require it to be NULL. This is not fan-out.

The diagnosis invalidated `fhir-prober` carryover but not `source-analyst`. It appended the dataset-wide finding “Lab Observation.valueQuantity can be synthesized from source text when valuenum is NULL” to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/blood_differential.md`. No attempt implementation artifact was edited. The next attempt must fix the comparator filter, then route only the expected charttime residual to the judge.
