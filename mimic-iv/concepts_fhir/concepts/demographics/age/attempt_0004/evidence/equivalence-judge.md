Evidence block

Concept: `age`, attempt `0004`.

Independent equivalence-judge verdict: `accept` for the `gap_shaped` review.

The full comparison has 431,231/431,231 keyed rows as `differing_null_only`; `anchor_age` and `anchor_year` are each NULL on all candidate rows. There are 0 conflicts, 0 only-candidate, and 0 only-oracle rows. Full-tuple identical fidelity is 0/431,231 only because the two declared unavailable columns differ; representable fidelity is 431,231/431,231 (100.00%).

The judge cited `MIMIC_NOTES.md:55-59` for the absence of MIMIC-specific Patient anchor extensions and `MIMIC_NOTES.md:128-147` for the non-recoverability of the separate anchor values, the collapse in `Patient.birthDate`, and the non-exact nature of minimum Encounter period year as an anchor-year substitute. Every defensible mapping was tried: the Patient extension inventory, `Patient.birthDate`, and `Encounter.period.start`; opaque resource keys were used only for equality joins. Typed SMALLINT NULLs are therefore faithful rather than estimates.

The judge found the loss ancillary: every admission, `hadm_id` key, one-row-per-admission grain, subject, admission time, and clinically meaningful derived `age` are preserved exactly; the missing anchor outputs do not change row inclusion, keys, grouping, carry-forward, or remaining values. The judge therefore accepted the divergence and did not block the concept.

Artifacts inspected by the judge:
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/concept.sql`
- `mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0004/unrepresentable.json`
- `mimic-iv/concepts_fhir/state/age/state.json`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`

The judge also observed that the current full warehouse no longer exhibits the previously recorded representable-column age/admission-time conflicts; this is recorded separately in the owned dataset fragment for human review.
