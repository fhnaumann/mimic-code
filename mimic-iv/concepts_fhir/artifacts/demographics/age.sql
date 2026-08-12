SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(e.admittime AS TIMESTAMP_NTZ) AS admittime,
    CAST(NULL AS SMALLINT) AS anchor_age,
    CAST(NULL AS SMALLINT) AS anchor_year,
    CAST(CAST(YEAR(CAST(e.admittime AS TIMESTAMP_NTZ)) - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ)) AS INTEGER) AS BIGINT) AS age
FROM encounter e
INNER JOIN patient p
    ON e.patient_key = p.patient_key
WHERE e.hadm_id_str IS NOT NULL
;
