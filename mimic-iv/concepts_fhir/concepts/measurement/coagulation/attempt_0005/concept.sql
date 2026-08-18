WITH filtered_rows AS (
    SELECT
        p.subject_id_str,
        p.patient_key,
        e.hadm_id_str,
        e.encounter_key,
        s.specimen_id_str,
        s.specimen_key,
        l.code,
        l.system,
        l.effective_datetime,
        l.effective_period_start,
        l.quantity_value,
        l.quantity_comparator,
        l.value_string
    FROM lab_observation l
    INNER JOIN patient p
        ON l.patient_key = p.patient_key
    INNER JOIN specimen s
        ON l.specimen_key = s.specimen_key
    LEFT JOIN encounter e
        ON l.encounter_key = e.encounter_key
    WHERE l.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems'
        AND l.code IN ('51196', '51214', '51297', '51237', '51274', '51275')
        AND l.quantity_value IS NOT NULL
        AND l.quantity_comparator IS NULL
        AND l.value_string IS NULL
),
numeric_rows AS (
    SELECT
        subject_id_str,
        patient_key,
        hadm_id_str,
        encounter_key,
        specimen_id_str,
        specimen_key,
        code,
        CAST(quantity_value AS DOUBLE) AS value_num,
        COALESCE(
            TRY_CAST(effective_datetime AS TIMESTAMP_NTZ),
            TRY_CAST(effective_period_start AS TIMESTAMP_NTZ)
        ) AS charttime
    FROM filtered_rows
),
lab_rows AS (
    SELECT
        CAST(subject_id_str AS INTEGER) AS subject_id,
        patient_key,
        CAST(hadm_id_str AS INTEGER) AS hadm_id,
        encounter_key,
        CAST(specimen_id_str AS INTEGER) AS specimen_id,
        specimen_key,
        code,
        value_num,
        charttime
    FROM numeric_rows
),
grouped AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(patient_key) AS patient_key,
        MAX(hadm_id) AS hadm_id,
        MAX(encounter_key) AS encounter_key,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(specimen_key) AS specimen_key,
        MAX(CASE WHEN code = '51196' THEN value_num ELSE NULL END) AS d_dimer,
        MAX(CASE WHEN code = '51214' THEN value_num ELSE NULL END) AS fibrinogen,
        MAX(CASE WHEN code = '51297' THEN value_num ELSE NULL END) AS thrombin,
        MAX(CASE WHEN code = '51237' THEN value_num ELSE NULL END) AS inr,
        MAX(CASE WHEN code = '51274' THEN value_num ELSE NULL END) AS pt,
        MAX(CASE WHEN code = '51275' THEN value_num ELSE NULL END) AS ptt
    FROM lab_rows
    GROUP BY specimen_id
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    patient_key,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    encounter_key,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    specimen_key,
    CAST(d_dimer AS DOUBLE) AS d_dimer,
    CAST(fibrinogen AS DOUBLE) AS fibrinogen,
    CAST(thrombin AS DOUBLE) AS thrombin,
    CAST(inr AS DOUBLE) AS inr,
    CAST(pt AS DOUBLE) AS pt,
    CAST(ptt AS DOUBLE) AS ptt
FROM grouped
;
