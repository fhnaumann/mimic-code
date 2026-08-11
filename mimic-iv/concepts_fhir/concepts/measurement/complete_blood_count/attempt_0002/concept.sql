WITH filtered_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        s.specimen_id_str,
        l.code,
        l.system,
        l.effective_datetime,
        l.effective_period_start,
        l.quantity_value,
        l.quantity_comparator
    FROM lab_observation l
    INNER JOIN patient p
        ON l.patient_key = p.patient_key
    INNER JOIN specimen s
        ON l.specimen_key = s.specimen_key
    LEFT JOIN encounter e
        ON l.encounter_key = e.encounter_key
    WHERE l.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems'
        AND l.code IN (
            '51221', '51222', '51248', '51249', '51250',
            '51265', '51279', '51277', '52159', '51301'
        )
        AND l.quantity_value IS NOT NULL
        AND l.quantity_comparator IS NULL
        AND CAST(l.quantity_value AS DOUBLE) > 0
), eligible_rows AS (
    SELECT
        CAST(subject_id_str AS INTEGER) AS subject_id,
        CAST(hadm_id_str AS INTEGER) AS hadm_id,
        CAST(specimen_id_str AS INTEGER) AS specimen_id,
        code,
        COALESCE(
            TRY_CAST(effective_datetime AS TIMESTAMP_NTZ),
            TRY_CAST(effective_period_start AS TIMESTAMP_NTZ)
        ) AS charttime,
        CAST(quantity_value AS DOUBLE) AS value_num
    FROM filtered_rows
), grouped AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(CASE WHEN code = '51221' THEN value_num ELSE NULL END) AS hematocrit,
        MAX(CASE WHEN code = '51222' THEN value_num ELSE NULL END) AS hemoglobin,
        MAX(CASE WHEN code = '51248' THEN value_num ELSE NULL END) AS mch,
        MAX(CASE WHEN code = '51249' THEN value_num ELSE NULL END) AS mchc,
        MAX(CASE WHEN code = '51250' THEN value_num ELSE NULL END) AS mcv,
        MAX(CASE WHEN code = '51265' THEN value_num ELSE NULL END) AS platelet,
        MAX(CASE WHEN code = '51279' THEN value_num ELSE NULL END) AS rbc,
        MAX(CASE WHEN code = '51277' THEN value_num ELSE NULL END) AS rdw,
        MAX(CASE WHEN code = '52159' THEN value_num ELSE NULL END) AS rdwsd,
        MAX(CASE WHEN code = '51301' THEN value_num ELSE NULL END) AS wbc
    FROM eligible_rows
    GROUP BY specimen_id
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    CAST(hematocrit AS DOUBLE) AS hematocrit,
    CAST(hemoglobin AS DOUBLE) AS hemoglobin,
    CAST(mch AS DOUBLE) AS mch,
    CAST(mchc AS DOUBLE) AS mchc,
    CAST(mcv AS DOUBLE) AS mcv,
    CAST(platelet AS DOUBLE) AS platelet,
    CAST(rbc AS DOUBLE) AS rbc,
    CAST(rdw AS DOUBLE) AS rdw,
    CAST(rdwsd AS DOUBLE) AS rdwsd,
    CAST(wbc AS DOUBLE) AS wbc
FROM grouped
;
