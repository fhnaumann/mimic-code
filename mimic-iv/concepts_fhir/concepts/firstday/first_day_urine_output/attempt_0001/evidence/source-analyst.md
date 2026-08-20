## Source analyst evidence

The canonical source SQL, DAG metadata, oracle manifest, source DDL, `MIMIC_NOTES.md`, and relevant urine-output/first-day fragments were read. The source joins `mimiciv_icu.icustays` to the completed `mimiciv_derived.urine_output` dependency with an inclusive `intime` through `intime + 1 day` window, then sums `urineoutput` by `subject_id, stay_id`. The candidate must consume the dependency as the `urine_output` temp view rather than rederive it. Manifest value columns are `subject_id INTEGER`, `stay_id INTEGER`, and `urineoutput DOUBLE`; required opaque key outputs are `patient_key` and `icu_encounter_key`.

Carryover was written and recorded at `mimic-iv/concepts_fhir/carryover/first_day_urine_output/source-analyst.md`. The outputevents effective-time DST-gap normalization quirk is already recorded in `MIMIC_NOTES.d/urine_output.md`; no new dataset-wide fragment entry was needed.
