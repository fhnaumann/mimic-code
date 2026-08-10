-- The selected POE code-status branch has no exact served FHIR representation.
-- This candidate intentionally preserves the representable chart Observation
-- branch; the omitted POE rows remain an intrinsic coverage gap.
WITH chart_rows AS (
    SELECT
        p.subject_id_str,
        h.hadm_id_str,
        i.stay_id_str,
        COALESCE(
            CAST(
                TRY_TO_TIMESTAMP(
                    REGEXP_REPLACE(
                        c.effective_datetime,
                        '(Z|[+-][0-9]{2}:[0-9]{2})$',
                        ''
                    ),
                    "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
                ) AS TIMESTAMP_NTZ
            ),
            CAST(
                TRY_TO_TIMESTAMP(
                    REGEXP_REPLACE(
                        c.effective_period_start,
                        '(Z|[+-][0-9]{2}:[0-9]{2})$',
                        ''
                    ),
                    "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
                ) AS TIMESTAMP_NTZ
            )
        ) AS charttime,
        CASE
            WHEN c.value_string IN ('Full code') THEN 1
            ELSE 0
        END AS fullcode,
        CASE
            WHEN c.value_string IN ('Comfort measures only') THEN 1
            ELSE 0
        END AS cmo,
        CASE
            WHEN c.value_string IN ('DNI (do not intubate)', 'DNR / DNI') THEN 1
            ELSE 0
        END AS dni,
        CASE
            WHEN c.value_string IN ('DNR (do not resuscitate)', 'DNR / DNI') THEN 1
            ELSE 0
        END AS dnr
    FROM cs_chart c
    LEFT JOIN cs_patient p
        ON c.patient_key = p.patient_key
    LEFT JOIN cs_icu i
        ON c.icu_encounter_key = i.icu_encounter_key
    LEFT JOIN cs_hosp h
        ON i.hosp_encounter_key = h.hosp_encounter_key
    WHERE c.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND c.item_code = '223758'
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(fullcode AS INTEGER) AS fullcode,
    CAST(cmo AS INTEGER) AS cmo,
    CAST(dni AS INTEGER) AS dni,
    CAST(dnr AS INTEGER) AS dnr
FROM chart_rows
;
