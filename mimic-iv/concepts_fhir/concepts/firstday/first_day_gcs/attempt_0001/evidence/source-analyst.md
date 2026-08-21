Evidence block

Concept: `first_day_gcs`, attempt 0001.

Read the canonical SQL, DAG metadata, authoritative `MIMIC_NOTES.md`, dependency `gcs.sql`, source DDL, and oracle manifest. DAG verification passed.

Findings: direct tables are `mimiciv_icu.icustays` and `mimiciv_derived.gcs`; upstream `gcs` reads `mimiciv_icu.chartevents`. Outputs are `subject_id INTEGER`, `stay_id INTEGER`, four FLOAT GCS values, and `gcs_unable INTEGER`, keyed by `stay_id`. Filters include the inclusive `intime - 6 hours` to `intime + 1 day` window, `gcs_seq = 1`, and exact itemids `223900, 223901, 220739`; the exact discriminator is `No Response-ETT`. Both joins are LEFT JOINs. The target uses `ROW_NUMBER`; upstream `gcs` uses `GROUP BY`, `MAX(CASE...)`, carry-forward logic, and a self-join. The relevant coding system is the chartevents `mimic-chartevents-d-items` system. The authoritative notes confirm that losing the No Response vs No Response-ETT label affects GCS outputs and minimum-row selection; no terminal decision was made.

Reusable analysis was written and recorded at `mimic-iv/concepts_fhir/carryover/first_day_gcs/source-analyst.md` and its carryover ledger. No immutable attempt artifacts were edited and no commit was made.
