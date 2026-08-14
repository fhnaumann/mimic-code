## Evidence

The independent equivalence judge read the full comparison, attempt artifacts, canonical SQL, and curated `MIMIC_NOTES.md`. It returned `blocked` / `BLOCKED_REPRESENTATION`.

The judge accepted the proven DST attribution as intrinsic upstream transformation loss: `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` normalizes charttime before writing `Observation.effectiveDateTime`; the comparator's full replay explains all 343 `only_candidate`, 1,105/1,106 `only_oracle`, and all 758 `differing_conflict` rows. The remaining one oracle-only group is the hard-coded omission at `mimic-fhir/sql/fhir_observation_chartevents.sql:34-37` for `(stay_id=34934165, charttime='2151-10-03 05:14:00')`; two selected item-220621 rows aggregate to one `glucose=96` vital-sign group in the oracle, but no Observation exists in FHIR.

Because the missing group changes row inclusion and the `(subject_id, stay_id, charttime)` semantic grain, the loss is essential despite its one-row magnitude. No FHIR query or resource identity can recover it, and no port fix exists. The judge required `uv run mimic_utils block vitalsign` with the cited explanation. No new note section was needed because the diagnostician already appended the hard-coded omission finding to `MIMIC_NOTES.d/vitalsign.md`.
