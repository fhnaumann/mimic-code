# Equivalence-judge evidence — sirs, attempt_0001

The independent judge ruled **accept** for the contested review. It confirmed
the four conflicts are wholly inherited from the judge-accepted
`first_day_vitalsign` DST transformation: `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`
casts source `chartevents.charttime` through `TIMESTAMPTZ` and writes the
normalized value to `Observation.effectiveDateTime`. Four occupied 02:00→03:00
collision groups (eight shifted raw rows) close all four SIRS conflicts with
no residual: two heart-rate score changes, two respiratory score changes, and
four total-score changes, affecting 4/73,181 output rows.

The original wall time is absent from semantic FHIR; `issued` is storetime and
resource IDs are opaque, so no valid query can recover it. The candidate
preserves the canonical dependency boundary, joins on opaque keys, preserves
the ordered score branches and NULL behavior, and performs no ID inversion.
The judge confirmed `first_day_bg_art` and `first_day_lab` are exact, while
`first_day_vitalsign` is a divergent-but-accepted dependency. The contract's
mandatory DST exemption applies even though the resulting score is clinically
meaningful. No new dataset-wide quirk was identified.
