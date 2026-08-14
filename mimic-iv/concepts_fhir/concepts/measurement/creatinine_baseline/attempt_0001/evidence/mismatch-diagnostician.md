# Mismatch-diagnostician evidence — creatinine_baseline attempt_0001

The diagnostician read the full comparison, attempt ViewDefinitions and SQL,
canonical source SQL, curated notes, dependency carryover, and the upstream
MIMIC-on-FHIR ETL. It classified the contested result as upstream
transformation loss inherited from the completed divergent dependency `age`,
not a fixable port bug.

The exact cause is `/Users/nau025/Documents/mimic-fhir/sql/fhir_patient.sql:15`,
which synthesizes `Patient.birthDate` from `MIN(transfers.intime) - anchor_age`,
and line 108 writes it to FHIR. The canonical age instead uses the
`anchor_year`/`anchor_age` basis. FHIR does not expose `anchor_age`,
`anchor_year`, or `anchor_year_group`, and opaque resource ids cannot recover
them. The candidate's served-data age expression is therefore the best
available mapping.

The full diff had 460 conflicts (age 460, mdrd_est 460, scr_baseline 85), no
row or schema gaps, and 430,771/431,231 identical rows. All 460 age conflicts
propagated to MDRD; 85 reached the baseline fallback branch. No carryover stage
was invalidated and no retry was recommended. Essentiality evidence was passed
to the judge: the inherited loss reaches clinically meaningful MDRD output and
85 `scr_baseline` values, although it changed no row inclusion/key/grouping in
this run.

No new notes fragment entry was appended; the transformation and age
propagation are already covered by curated `MIMIC_NOTES.md` and the contract.
