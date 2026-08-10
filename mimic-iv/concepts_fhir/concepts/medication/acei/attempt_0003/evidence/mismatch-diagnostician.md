Evidence block — concept `acei`, stage `mismatch-diagnostician`, attempt 0003.

The full result is a fixable port bug, not yet judge-ready. Schema matched;
the unkeyed full-tuple comparison reported oracle 112,014 rows, candidate
111,828, 9,234 only-oracle tuples, and 9,048 only-candidate tuples.

Diagnosis: the direct Medication view handled only top-level
`mimic-medication-name` identifiers. It omitted medication-mix requests whose
source drugs are represented by repeated
`Medication.ingredient.itemReference` components. This drops 186 full-data
rows, all concentrated in `Enalaprilat` (oracle 776 versus candidate 590).
The exact affected artifacts are
`attempt_0003/ViewDefinition.medication.json` and `concept.sql`; the analysis
gap is in `carryover/acei/fhir-prober.md` at its direct-medication-only
mapping. The next attempt must add an ingredient/component branch and union it
with the direct branch without deduplicating ingredient multiplicity.

The remaining 9,048 candidate-only tuples are not fan-out: 9,034 are NULL
timestamp substitutions (9,025 invalid intervals and 9 incomplete endpoints),
and 14 are DST-normalized timestamp tuples. The corresponding intrinsic losses
are cited to `mimic-fhir/sql/fhir_medication_request.sql:172-177` (validity
period omitted) and `:43-44` (TIMESTAMPTZ normalization). The medication-mix
omission is fixable and must be addressed before the judge.

Upstream mix evidence: `mimic-fhir/sql/fhir_medication_request.sql:12-37,76`,
`mimic-fhir/sql/medication/medication_mix.sql:27-53,80-84`, and
`mimic-fhir/sql/medication/medication_prescriptions.sql:19-54` preserve the
pharmacy grouping, repeated ingredient references, and source drug names.
The diagnosis recommended invalidating the `fhir-prober` carryover stage;
`source-analyst` remains valid. Existing MIMIC_NOTES.md entries on medication
identifiers, omitted validity periods, and TIMESTAMP_NTZ were updated with
this evidence; no duplicate note was added. No immutable artifact was edited.
