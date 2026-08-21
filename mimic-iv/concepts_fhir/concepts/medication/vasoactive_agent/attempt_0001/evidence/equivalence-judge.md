# Equivalence judge evidence

**accept**

The contested divergence is wholly inherited. Upstream `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9` casts `inputevents.starttime/endtime` through `TIMESTAMPTZ`, and lines 61-69 write only those transformed values to `MedicationAdministration.effective.ofType(Period).start/end`. The original wall time is absent and cannot be recovered by any FHIR query or opaque resource identity.

Full-source evidence identifies 112 shifted administrations among 614,600 dependency rows (0.0182%): 2 dobutamine, 4 milrinone, 58 norepinephrine, 47 phenylephrine, and 1 vasopressin; dopamine and epinephrine contribute no timing residual. Their second-order propagation through `UNION DISTINCT`, `LEAD`, and interval containment explains the target’s +21 rows (0.0032%). The 594,266/594,287 residual halves are not affected-row counts: exact float differences from six-decimal Quantity materialization prevented unkeyed pairing, although dependency values were within tolerance.

The sole additional source gap is one phenylephrine administration requiring absent `patientweight` (1/193,260, 0.00052%). The dependency honestly emits NULL; timing, inclusion, and grain remain intact. `linkorderid` is also absent but is not consumed by this parent. No essential loss requires blocking: proven DST damage is explicitly exempt, the patientweight gap is ancillary and inherited, and wholly inherited divergence must be accepted rather than re-tested for essentiality.

Acceptance justification: “`vasoactive_agent` faithfully reproduces canonical interval construction. All substantive divergence is inherited from seven judge-accepted dependencies: rare endpoint normalization caused by `TIMESTAMPTZ` casts at `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9`, serialized exclusively to `MedicationAdministration.effectivePeriod.start/end` at lines 61-69, six-decimal Quantity representation, and one ancillary phenylephrine patientweight NULL. The original wall times, low-order precision, and patientweight are absent from semantic FHIR elements and cannot be recovered through opaque resource IDs. The target introduces no independent mapping or SQL loss.”

## Evidence block

Concept: `vasoactive_agent`. Attempt: `attempt_0001`. Verdict: accept. Tier: contested; classification: unavailable_no_key.

Assessed divergence: oracle 665,529 rows versus candidate 665,550, delta +21. The unpaired multiset residual was 594,266 only-oracle and 594,287 only-candidate with zero paired rows; these ambiguous counts are comparison artifacts, not evidence of missing or invented rows.

Fidelity figures: `identical_fraction` is null/unavailable; `representable_fraction` was not emitted and is likewise unavailable because the unkeyed residual did not pair and there was no target declaration.

FHIR/ETL citations: `MedicationAdministration.effective.ofType(Period).start/end`, written from transformed endpoints by `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9,61-69`; `MedicationAdministration.dosage.rateQuantity.value`, subject to six-decimal served precision (`:14,91-99`); and no MedicationAdministration dosage or supporting-information path carrying `inputevents.patientweight` (`:7-23,38-103`).

Divergent dependencies: dobutamine, dopamine, epinephrine, milrinone, norepinephrine, phenylephrine, and vasopressin—all judge-accepted. Timing divergence propagates from five; dopamine/epinephrine’s absent `linkorderid` does not propagate because the parent never consumes it.

Relevant curated `MIMIC_NOTES.md` entries: “FHIR datetimes carry an offset—cast to TIMESTAMP_NTZ” and its ICU MedicationAdministration DST section; “ICU MedicationAdministration Quantity values are served at decimal scale six”; “ICU MedicationAdministration omits inputevent linkorderid”; “Polymorphic fields mix datatypes across rows”; and the opaque-resource-identity rule. Their documented workarounds were applied.

Rationale: Candidate `concept.sql:70-161` reproduces canonical `vasoactive_agent.sql:9-127`; the supporting Encounter join is one-to-one, and no resource identifier is parsed. Rates do not control interval construction, so precision loss only affects exact residual alignment; structural differences arise from the 112 proven endpoint transformations. The one patientweight NULL remains an ancillary inherited value gap. Consequently there is no target bug and no essential target-originated loss requiring `blocked`.

Curated-note promotion candidate: claim that ICU MedicationAdministration omits source `inputevents.patientweight`, affecting `MedicationAdministration.dosage`/`supportingInformation`; the exhaustive ETL projection at `fhir_medication_administration_icu.sql:7-23,38-103` never selects or serializes patientweight, and full phenylephrine evidence found one exercised normalization row.
