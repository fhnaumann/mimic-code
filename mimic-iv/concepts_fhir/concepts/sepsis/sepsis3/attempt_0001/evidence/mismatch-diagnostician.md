Concept `sepsis3`; attempt_0001 divergence diagnosis.

The full result is `review`, tier `contested`: 32,971 oracle rows versus
32,794 candidate, 32,414 identical, 380 `differing_conflict`, 177
`only_oracle`, and zero `only_candidate`/`differing_null_only`. DST attribution
explained 0/380. The target's schema and clinical `sepsis3` value are exact.

Root cause is wholly inherited divergence, not a target port bug. The target
SQL at `concept.sql:1-77` faithfully preserves `sepsis3.sql:9-80`: SOFA `>=2`,
opaque ICU-key join, inclusive `[-48h,+24h]` window, per-stay partition and
source ordering. It consumes completed `sofa` and
`suspicion_of_infection` views and introduces no independent clinical
rederivation or fan-out.

The medication/suspicion inheritance is cited to
`mimic-fhir/sql/fhir_medication_request.sql:172-177`: invalid/incomplete
prescription intervals omit `dispenseRequest.validityPeriod` endpoints;
`authoredOn` is not a substitute and opaque ids cannot recover them. The
accepted suspicion dependency propagates this through its `ab_id` ordering and
culture windows, producing multi-hour/day antibiotic-time conflicts, altered
culture/suspicion times, selected SOFA-hour changes, and 177 omitted stays.
The sample for stay `36448639` moved the suspicion anchor from
`2168-09-10 08:33` to `2168-09-14 10:59`, moving the SOFA selection from
`2168-09-10 12:00` to `2168-09-12 11:00` and changing coagulation 0→3,
cardiovascular 1→4, and SOFA 2→8.

The accepted SOFA dependency's smaller inherited loss is Pathling's
`DECIMAL(32,6)` materialization of FHIR decimals. The ETL writes the rate
unchanged at `mimic-fhir/sql/fhir_medication_administration_icu.sql:14,91-99`
(especially line 94); the irreversible encoder truncation changes threshold
inputs in `mimic-iv/concepts/score/sofa.sql:278-285` and is amplified by its
24-row window at `:370-375`. Other target conflicts are changed-hour
selection effects caused by the shifted suspicion anchor.

The run used the 2026-08-26 rebuilt warehouse. Antibiotic attempt_0004 on the
same warehouse had zero remaining DST conflicts, and this target's replay
attributed 0/380; observed differences are often hours/days. Therefore this is
neither an old build nor an unreached DST path, and the DST fix does not explain
the target result.

Essentiality at the target level is inherited: the accepted dependencies can
affect row inclusion (177 stays), ordering, clinically meaningful times,
selected SOFA hour, components, and total score, while the target retains one
row per `stay_id` and invents no rows. Per the dependency contract, remediation
belongs to dependency-order upstream replays, not a re-authored sepsis3 query.
No carryover stage is faulty; no invalidation and no semantic-rework counter
are recommended.

Relevant fragments were checked only as unconfirmed leads: the named
`suspicion_of_infection.md`/`sofa.md` claims were not present in their current
content, and no `antibiotic.md` exists. The diagnosis was independently
confirmed from curated `MIMIC_NOTES.md` and completed dependency artifacts; no
fragment was appended and no new dataset-wide quirk was reported.

Artifacts read included the target comparison/run metadata/SQL/ViewDefinitions,
canonical source, dependency attempts and states, `LOOP_CONTRACT.md`,
`MIMIC_NOTES.md`, and the explicitly named fragments. No files were edited or
committed.
