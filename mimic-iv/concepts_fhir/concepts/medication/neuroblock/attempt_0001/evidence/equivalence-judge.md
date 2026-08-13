# Equivalence-judge evidence — neuroblock

The independent judge reviewed the contested VOID DIFF, all attempt artifacts,
the canonical source semantics, curated MIMIC_NOTES.md, ETL evidence, and the
diagnostician report. Verdict: **blocked**. `inputevents.orderid` is selected
by the source, is a source row-identity component, and is the manifest key,
but ICU MedicationAdministration carries no independent representation:
identifier, request, and request.identifier.value are populated on 0/20,404
resources. The ETL uses it only in opaque UUID generation at
`mimic-fhir/sql/fhir_medication_administration_icu.sql:20` and writes the UUID
as resource identity at lines 40–44; resource IDs cannot be inverted. Typed
NULL is therefore not a faithful ancillary-column omission. The missing
identity/key information is essential under LOOP_CONTRACT.md:309–340, so the
whole concept cannot be published. There are no divergent dependencies and no
fixable port bug.

The comparator's 14,174 `only_candidate` and 28,348 `only_oracle` counts are
VOID DIFF artefacts; no rows aligned, so representable fidelity is unavailable
(headline identical 0/14,174, 0.00%). No new dataset-wide note was appended:
the orderid omission is already recorded in the concept-owned fragment.
