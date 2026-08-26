## Mismatch diagnostician evidence

The residual is a contested review, not a mechanical mismatch. The
diagnostician read the canonical SQL, both attempts, carryover, curated notes,
manifest, run metadata, and full comparison. It distinguished divergent
dependencies `dobutamine`, `dopamine`, `epinephrine`, `norepinephrine`, and
`vitalsign` from SOFA-owned logic.

Conclusion: attempt_0002 is a faithful port with an intrinsic served-data
conflict; no further SQL or ViewDefinition defect is evidenced. Attempt_0001's
local untyped-literal Spark bug was fixed: attempt_0002 correctly compares
FLOAT rates with FLOAT thresholds. The remaining loss is inherited through
the vasoactive dependencies: Pathling rounds FHIR decimal Quantity values to
six places before the dependency publishes FLOAT rates. A source rate just
above a clinical cut-point can therefore be served as `0.100000` or
`5.000000`, indistinguishable from the exact threshold.

Conflict accounting: 294 current-hour `cardiovascular` rows differ; 1,022
`cardiovascular_24hours` rows and the same 1,022 `sofa_24hours` rows differ via
the canonical 24-row `ROWS BETWEEN 23 PRECEDING AND 0 FOLLOWING` window; one
row differs directly on `rate_norepinephrine`. All other components agree and
there are no missing/extra/null-only rows. This pattern rules out a SOFA-local
join, cohort, aggregation, or window defect. The corrected threshold logic is
at attempt_0002 `concept.sql:232-242`; canonical score/window logic is
`mimic-iv/concepts/score/sofa.sql:278-288,370-375`.

The contested upstream provenance is
`mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`, especially
line 94, which writes the selected source rate into
`MedicationAdministration.dosage.rateQuantity.value`. The subsequent
Pathling `DECIMAL(32,6)` encoder discards the discriminating digits; companion
scale/canonicalized fields derive from the rounded value, and opaque resource
ids cannot be used as a recovery channel. No query over the served FHIR data
can establish which side of the threshold the source occupied. The relevant
curated notes are the six-decimal Quantity entry and the
`DECIMAL(32,6)` Pathling entry; sibling medication fragments were treated as
provisional leads.

Result: upstream transformation loss; do not edit or retry SOFA. No carryover
stage is faulty. The conflict reaches clinically meaningful cardiovascular and
total SOFA scores, so the equivalence judge must apply the essential-loss
policy and decide the terminal outcome.

Artifacts/read checks: attempt_0002 `comparison.full.json`, `run_meta.full.json`,
`hpc_accounting.json`, SQL, ViewDefinition, prior evidence, carryover files,
oracle manifest, canonical SQL, `MIMIC_NOTES.md`, and this evidence file. No
artifact or fragment was edited by the diagnostician; no commit was made.
