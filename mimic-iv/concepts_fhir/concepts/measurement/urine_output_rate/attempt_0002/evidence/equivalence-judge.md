# Equivalence-judge evidence — `urine_output_rate`, attempt 0002

The independent judge returned **accept** for the contested review.

The judge confirmed that `mimic-fhir/sql/fhir_observation_outputevents.sql:9,60,62-65`
writes outputevents `charttime` after an irreversible `TIMESTAMPTZ` cast,
while `fhir_observation_chartevents.sql:9,67` and
`fhir_encounter_icu.sql:31-32,97-100` similarly normalize direct timing inputs.
The original wall times are not serialized elsewhere and cannot be recovered
by a valid FHIR query; resource ids remain opaque.

The full counts close: 393 `only_oracle` rows split into 157 re-paired rows and
236 key collisions, all 157 `only_candidate` rows re-pair, and both unpaired
residuals are zero. Of 1,417 conflicts, 232 are collision counterparts and
1,185 are second-order effects propagated through the concept's LAG, grouped
rolling windows, rates, and weight interval join. The cited completed
dependencies are `urine_output` and `weight_durations`; no candidate-specific
residual remains. The 393 shifted rows are 0.0118% of 3,321,747, consistent
with DST-gap rarity.

Although the shift affects keys, row inclusion, windows, and rates, the
contract explicitly treats proven upstream DST normalization and second-order
effects as accepted upstream defect rather than essential representation loss.
Attempt 0001's hour-boundary bug was fixed in attempt 0002 and no mapping was
recovered through opaque ids. The judge cited `MIMIC_NOTES.md:423-528` and
`:203-230,241-267`; no new notes fragment entry was required.
