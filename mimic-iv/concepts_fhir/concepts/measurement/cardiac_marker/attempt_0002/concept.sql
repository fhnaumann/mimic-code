WITH filtered_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        s.specimen_id_str,
        l.code,
        l.system,
        l.effective_datetime,
        l.effective_period_start,
        l.quantity_value
    FROM lab_observation l
    INNER JOIN patient p
        ON l.patient_key = p.patient_key
    INNER JOIN specimen s
        ON l.specimen_key = s.specimen_key
    LEFT JOIN encounter e
        ON l.encounter_key = e.encounter_key
    WHERE l.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems'
        AND l.code IN ('51003', '50911', '50963')
        AND l.quantity_value IS NOT NULL
),
numeric_rows AS (
    SELECT
        subject_id_str,
        hadm_id_str,
        specimen_id_str,
        code,
        COALESCE(effective_datetime, effective_period_start) AS effective_text,
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
        COALESCE(
            TRY_CAST(effective_text AS TIMESTAMP_NTZ),
            CAST(
                TRY_TO_TIMESTAMP(
                    effective_text,
                    "yyyy-MM-dd'T'HH:mm:ssXXX"
                ) AS TIMESTAMP_NTZ
            )
        ) AS charttime
    FROM numeric_rows
),
grouped AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(CASE WHEN code = '51003' THEN value_num ELSE NULL END) AS troponin_t,
        MAX(CASE WHEN code = '50911' THEN value_num ELSE NULL END) AS ck_mb,
        MAX(CASE WHEN code = '50963' THEN value_num ELSE NULL END) AS ntprobnp
    FROM lab_rows
    GROUP BY specimen_id
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    CAST(troponin_t AS DOUBLE) AS troponin_t,
    CAST(ck_mb AS DOUBLE) AS ck_mb,
    CAST(ntprobnp AS DOUBLE) AS ntprobnp
FROM grouped
;
