## Evidence

The source analyst read `mimic-iv/concepts/measurement/icp.sql`, the `icp` DAG node and SHA, the PostgreSQL DDL for `mimiciv_icu.chartevents`, `MIMIC_NOTES.md`, relevant provisional fragments, and `mimic-fhir/sql/fhir_observation_chartevents.sql`. The canonical source is dependency-free and filters chartevents itemids 220765 and 227989, preserves rows while nulling values outside `(0, 100)`, then emits `MAX(icp)` grouped by `(subject_id, stay_id, charttime)`. Expected output is `subject_id INTEGER`, `stay_id INTEGER`, `charttime TIMESTAMP`, and nullable `icp FLOAT`.

Reusable analysis was produced at `mimic-iv/concepts_fhir/carryover/icp/source-analyst.md`. The agent also appended the dataset-wide chartevents omission finding to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/icp.md`. No implementation artifacts were authored.
