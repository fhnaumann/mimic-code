SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
    TRY_CAST(e.period_start AS TIMESTAMP_NTZ) AS admittime,
    CAST(NULL AS SMALLINT) AS anchor_age,
    CAST(NULL AS SMALLINT) AS anchor_year,
    CAST(
        YEAR(TRY_CAST(e.period_start AS TIMESTAMP_NTZ))
        - YEAR(TRY_CAST(p.birth_date AS DATE))
        AS BIGINT
    ) AS age,
    p.patient_key,
    e.encounter_key
FROM encounter e
INNER JOIN patient p
    ON e.patient_key = p.patient_key
WHERE e.hadm_id_str IS NOT NULL
;
