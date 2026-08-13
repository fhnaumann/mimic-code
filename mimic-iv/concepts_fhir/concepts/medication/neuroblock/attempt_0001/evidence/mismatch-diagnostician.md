# Mismatch-diagnostician evidence — neuroblock

Read the full comparison, attempt implementation, declaration, source and
FHIR carryover, curated MIMIC_NOTES.md, and the ICU MedicationAdministration
ETL. Found no fixable implementation or carryover fault. The VOID DIFF is
caused by the declared-unrepresentable `inputevents.orderid` being the
manifest key: the candidate's typed NULL prevents keyed alignment, so the
14,174 `only_candidate` and 28,348 `only_oracle` counts are key-selection
artefacts rather than evidence of fan-out or filtering. The ETL uses orderid
only to construct the opaque resource UUID at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:20`, serializing that
identity at lines 40–44 and no independent identifier/request field in the
semantic output. The prober's 0/20,404 identifier/request evidence confirms
the gap. Because orderid is an output and source row-identity component, the
loss is essential under LOOP_CONTRACT.md; recommendation is judge
consideration of whole-concept blocking, not a retry. No carryover stage was
invalidated and no files were committed.
