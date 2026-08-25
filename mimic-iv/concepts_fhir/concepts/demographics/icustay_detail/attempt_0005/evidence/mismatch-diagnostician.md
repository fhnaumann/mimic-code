# Diagnosis evidence — `icustay_detail`

The 11,501 `race` conflicts are upstream MIMIC-on-FHIR transformation loss,
not a port bug. The canonical query emits the ICU stay's admission race at
`mimic-iv/concepts/demographics/icustay_detail.sql:14,43-47`. The FHIR ETL
selects one latest-admission patient race at `mimic-fhir/sql/fhir_patient.sql:17,23-30,59,110`,
writes only the mapped extension via
`mimic-fhir/sql/fn/fn_patient_extension.sql:11-30,60-63`, and applies the
non-injective OMB mapping at `mimic-fhir/sql/fhir_etl/map_race_omb.sql:13-45`.
The hospital Encounter does not preserve admission race
(`mimic-fhir/sql/fhir_encounter.sql:59-71,149-169`), so earlier-admission
selection and detailed-to-OMB collapse cannot be inverted by any query.

The replayed attempt already projects both race and ethnicity extensions and
decodes their values in `concept.sql`; resource IDs remain opaque and are not a
recovery mechanism. Attempt 0005 repeats the same 11,501 race conflicts as
attempt 0004 while the rebuilt warehouse removes the prior age and datetime
conflicts.

`hospital_expire_flag` is correctly emitted as `CAST(NULL AS SMALLINT)` at
`attempt_0005/concept.sql:115` and is confirmed by the comparator declaration.
The 61,680 `differing_null_only` rows are the declared admission-scoped FHIR
coverage gap; the remaining rows are classified under the race conflict.

No carryover stage is blamed, no sibling fragment was used, no fragment entry
was appended, and no implementation artifact was modified. The full comparison,
replay metadata, source analyses, and cited upstream ETL files were reviewed.
