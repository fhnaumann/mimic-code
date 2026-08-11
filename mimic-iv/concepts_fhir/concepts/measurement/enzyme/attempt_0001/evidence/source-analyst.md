## Evidence

Concept: `enzyme`.

Read the canonical `mimic-iv/concepts/measurement/enzyme.sql`, the loop contract, curated MIMIC notes, relevant lab fragments, DAG entry, source DDL, oracle manifest, and relevant FHIR ETL SQL.

The source reads only `mimiciv_hosp.labevents`, filters exact itemids `50861, 50863, 50878, 50867, 50885, 50884, 50883, 50910, 50911, 50927, 50954`, requires non-NULL `valuenum > 0`, and groups by `specimen_id`. It outputs `subject_id`, `hadm_id`, `charttime`, `specimen_id`, and eleven analyte MAX pivots (`alt`, `alp`, `ast`, `amylase`, `bilirubin_total`, `bilirubin_direct`, `bilirubin_indirect`, `ck_cpk`, `ck_mb`, `ggt`, `ld_ldh`). The oracle natural key is `specimen_id`; the manifest contains 1,639,514 rows.

FHIR mapping requires labevents-derived Observations, exact proprietary lab-item coding, numeric Quantity values, Observation specimen references to lab Specimen identifiers, Patient identifier values cast to INTEGER, and LEFT-join handling for incomplete hospital Encounter references. Quantity aliases require numeric casts; datetime values require TIMESTAMP_NTZ handling. No derived dependency or terminology translation is involved.

Produced/reused artifact: `mimic-iv/concepts_fhir/carryover/enzyme/source-analyst.md` (recorded with `mimic_utils carryover-record enzyme --stage source-analyst`). No ViewDefinition, concept SQL, or commit was created at this stage.
