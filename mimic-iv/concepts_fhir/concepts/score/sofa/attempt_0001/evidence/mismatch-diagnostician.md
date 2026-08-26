## Mismatch diagnostician evidence

The full result was a contested review, not a mechanical mismatch. The
diagnostician read the canonical SOFA SQL, curated notes, source/FHIR
carryover, attempt SQL/ViewDefinition, manifest, comparison, run metadata,
stage evidence, and the concept-equivalence guidance. Divergent dependencies
were explicitly considered: `dobutamine`, `dopamine`, `epinephrine`,
`norepinephrine`, and `vitalsign`.

Root cause: inherited six-decimal ICU MedicationAdministration rate precision
loss combines with a SOFA-local Spark type-coercion bug. The dependency views
publish vasoactive rates as `FLOAT`; Pathling's served decimal value can be
`0.100000`, materializing as float32 `0.10000000149011612`. The SOFA CASE
compared this FLOAT to an untyped `0.1`, making a threshold value greater and
assigning cardiovascular score 4 instead of the oracle's 3. The sample in
`comparison.full.json` shows candidate norepinephrine
`0.10000000149011612`, oracle `0.09999998658895493`, and score 4 versus 3.
The 24-row window propagates current-score errors into
`cardiovascular_24hours`/`sofa_24hours`, explaining the conflict shape. MAP
was not conflicting; DST attribution explained 0/1,938 rows.

Correction for the next attempt: explicitly cast all cardiovascular numeric
threshold literals (`0.1`, `15`, `5`, and `0` as used) to `FLOAT` before CASE
evaluation. Do not add epsilon, round toward the oracle, or change strict
comparisons. Output casts occur too late to fix the CASE. No carryover stage is
faulty; invalidate none. The inherited six-decimal loss may leave a smaller
intrinsic residual after this local bug is corrected.

For the residual case, the semantic FHIR path is
`mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99` (especially
line 94), which writes `ie_RATE` into
`MedicationAdministration.dosage.rateQuantity.value`. The six-decimal
materialization itself is Pathling encoder behavior, not a mimic-fhir SQL
defect; discarded digits are absent from queryable FHIR and resource ids are
opaque. Attempt `0001`, however, is a fixable bug until the local threshold
coercion is corrected.

Result: semantic rework is required. No files or fragments were written by the
diagnostician and no commit was made. This evidence supports the required
semantic failure and a new immutable attempt.
