# Mismatch-diagnostician evidence — charlson attempt 0001

The diagnostician read the full comparison, attempt artifacts, canonical
Charlson and age SQL, authoritative MIMIC_NOTES, and the relevant carryovers.
It diagnosed inherited upstream transformation loss, not a port bug. The
candidate's age expression and threshold logic match the canonical dependency
and Charlson arithmetic exactly; all 17 diagnosis flags, identifiers, and row
inclusion agree. The 61 conflicts are threshold crossings among the 460 known
age conflicts, so both `age_score` and the unit-weighted index are one higher
on those rows.

Required ETL citation: `mimic-fhir/sql/fhir_patient.sql:15` synthesizes
`Patient.birthDate` from `MIN(transfers.intime) - anchor_age` (written at line
108), while canonical `mimic-iv/concepts/demographics/age.sql:30` requires the
anchor pair. `anchor_year` and an equivalent discriminator are not carried by
FHIR, so no query can recover the oracle age exactly. Encounter period timing
comes from `mimic-fhir/sql/fhir_encounter.sql:65,149-151`; its DST issue does
not affect year extraction here.

Effect: 61/431,231 rows (0.014%) conflict in `age_score` and
`charlson_comorbidity_index`; there are no only-oracle, only-candidate, or
null-only rows. No carryover stage should be invalidated, and no notes entry was
appended.
