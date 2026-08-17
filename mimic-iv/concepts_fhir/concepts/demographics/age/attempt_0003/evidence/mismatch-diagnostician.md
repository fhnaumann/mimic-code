# Evidence: mismatch-diagnostician

The diagnostician read the authoritative contract, curated MIMIC notes, the
canonical source SQL, current attempt artifacts, the full comparison, age
carryover, and the upstream MIMIC-FHIR SQL. It did not read or cite provisional
fragments; the orchestrator found no relevant sibling fragment.

## Diagnosis

The 460 residual `age` conflicts are upstream transformation loss, not a
fixable candidate bug. The oracle formula is at
`mimic-iv/concepts/demographics/age.sql:30`. The upstream FHIR transform at
`mimic-fhir/sql/fhir_patient.sql:15` computes `Patient.birthDate` as
`CAST(CAST(MIN(tfs.intime) AS DATE) - CAST(pat.anchor_age || 'years' AS INTERVAL) AS DATE)`
and writes it at line 108. The candidate's
`YEAR(period_start) - YEAR(birth_date)` therefore reduces to an age based on
`year(MIN(transfers.intime))`, not the unrecoverable relational anchor pair.
This explains 460/431,231 age conflicts (0.107%). The oracle correction is not
stored in Patient or another FHIR element, and no FHIR query can recover it.

The candidate's year subtraction preserves the canonical year-boundary
semantics and is the best representable mapping. The 44/431,231 `admittime`
conflicts are separately and exhaustively attributed to the upstream DST cast
at `mimic-fhir/sql/fhir_encounter.sql:65`. No resource ID parsing or inversion
was used. `anchor_age` and `anchor_year` are valid typed-NULL declarations;
they are ancillary because row inclusion, grain, and the `hadm_id` key remain
unchanged (431,231 rows on both sides, no only-oracle or only-candidate rows).

No carryover stage should be invalidated and no retry is recommended. The
diagnosis is not a terminal decision; the equivalence judge must decide the
review.

## Evidence paths

- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/comparison.full.json`
- `mimic-iv/concepts/demographics/age/attempt_0003/concept.sql`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0003/unrepresentable.json`
- `mimic-iv/concepts/demographics/age.sql`
- `mimic-fhir/sql/fhir_patient.sql:15,108`
- `mimic-fhir/sql/fhir_encounter.sql:65`

No files were edited or produced by the diagnostician and no commit was made.
