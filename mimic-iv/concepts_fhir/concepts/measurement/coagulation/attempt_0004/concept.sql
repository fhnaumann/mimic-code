WITH filtered_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        s.specimen_id_str,
        l.code,
        l.system,
        l.effective_datetime,
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
        hadm_id_str,
        specimen_id_str,
        code,
        effective_datetime,
        CAST(quantity_value AS DOUBLE) AS value_num
    FROM filtered_rows
),
lab_rows AS (
    SELECT
        CAST(subject_id_str AS INTEGER) AS subject_id,
        CAST(hadm_id_str AS INTEGER) AS hadm_id,
        CAST(specimen_id_str AS INTEGER) AS specimen_id,
        code,
        value_num,
        TRY_CAST(effective_datetime AS TIMESTAMP_NTZ) AS charttime
    FROM numeric_rows
),
grouped AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
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
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    CAST(d_dimer AS DOUBLE) AS d_dimer,
    CAST(fibrinogen AS DOUBLE) AS fibrinogen,
    CAST(thrombin AS DOUBLE) AS thrombin,
    CAST(inr AS DOUBLE) AS inr,
    CAST(pt AS DOUBLE) AS pt,
    CAST(ptt AS DOUBLE) AS ptt
FROM grouped
;
