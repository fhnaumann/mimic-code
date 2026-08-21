Concept `suspicion_of_infection`; source-analyst evidence.

The agent checked the DAG, canonical SQL, dependency `antibiotic`, relevant MIMIC-IV schemas, the oracle manifest, `LOOP_CONTRACT.md`, and `MIMIC_NOTES.md`. The canonical source is `mimic-iv/concepts/sepsis/suspicion_of_infection.sql`. It uses `mimiciv_derived.antibiotic` and `mimiciv_hosp.microbiologyevents`, with left joins, 72-hour/24-hour temporal windows, `GROUP BY`, `MAX`, and `ROW_NUMBER` logic. The literal coding filter is organism `org_itemid != 90856`; no ICD codes are used. The natural key is `(subject_id, ab_id)`, with one output row per antibiotic dependency record. No FHIR/resource IDs were reconstructed.

Reusable artifact: `mimic-iv/concepts_fhir/carryover/suspicion_of_infection/source-analyst.md`.
