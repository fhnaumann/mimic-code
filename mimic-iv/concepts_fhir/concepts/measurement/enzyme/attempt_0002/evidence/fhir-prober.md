## Evidence

Concept: `enzyme`.

Reused the recorded FHIR mapping from `mimic-iv/concepts_fhir/carryover/enzyme/fhir-prober.md` after `mimic_utils carryover enzyme` marked `fhir-prober` reusable. The mapping uses labevents-derived Observation resources, exact `mimic-d-labitems` string codes, Quantity values, the Specimen identifier grouping spine, Patient/Encounter identifier values, a LEFT Encounter join, and `TIMESTAMP_NTZ` wall-clock handling. The prior probe found one intrinsic DST-gap shift and no new dataset-wide quirk.

Artifact reused: `mimic-iv/concepts_fhir/carryover/enzyme/fhir-prober.md`. No new FHIR probe was needed.
