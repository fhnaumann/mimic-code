## Evidence

The source analysis read the canonical `mimic-iv/concepts/measurement/blood_differential.sql`, DAG metadata, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the available notes protocol, source schema/DDL, generated dialect SQL, the oracle manifest, and downstream `first_day_lab.sql`.

The concept is level 0 with no dependencies and uses `mimiciv_hosp.labevents`, grouped by `specimen_id`. It filters the exact active itemids `51146, 52069, 51199, 51200, 52073, 51244, 51245, 51133, 52769, 51253, 51254, 52074, 51256, 52075, 51143, 51144, 51218, 52135, 51251, 51257, 51300, 51301, 51755`, plus non-null, non-negative `valuenum`. It pivots analytes with conditional `MAX`, computes WBC/percentage-driven absolute-value imputations, divides itemids `51199`, `52769`, `51253`, and `51218` by 1000, and rounds absolute outputs to four decimals. The output has 20 columns and natural key `specimen_id`; `granulocytes_abs` is internal and omitted.

Reusable analysis was written to `mimic-iv/concepts_fhir/carryover/blood_differential/source-analyst.md` and recorded with the carryover controller. No attempt artifact was modified by the analyst.
