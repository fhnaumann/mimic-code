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
        AND l.code IN (
            '50862', '50930', '50976', '50868', '50882', '51006',
            '50893', '50902', '50912', '50931', '50983', '50971'
        )
        AND l.quantity_value IS NOT NULL
        AND l.quantity_comparator IS NULL
        AND l.value_string IS NULL
), numeric_rows AS (
    SELECT
        CAST(subject_id_str AS INTEGER) AS subject_id,
        CAST(hadm_id_str AS INTEGER) AS hadm_id,
        CAST(specimen_id_str AS INTEGER) AS specimen_id,
        code,
        TRY_CAST(effective_datetime AS TIMESTAMP_NTZ) AS effective_datetime_ntz,
        TRY_CAST(effective_period_start AS TIMESTAMP_NTZ) AS effective_period_start_ntz,
        CAST(quantity_value AS DOUBLE) AS value_num
    FROM filtered_rows
), eligible_rows AS (
    SELECT
        subject_id,
        hadm_id,
        specimen_id,
        code,
        COALESCE(effective_datetime_ntz, effective_period_start_ntz) AS charttime,
        value_num
    FROM numeric_rows
    WHERE value_num > 0 OR code = '50868'
), grouped AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(CASE WHEN code = '50862' AND value_num <= 10 THEN value_num ELSE NULL END) AS albumin,
        MAX(CASE WHEN code = '50930' AND value_num <= 10 THEN value_num ELSE NULL END) AS globulin,
        MAX(CASE WHEN code = '50976' AND value_num <= 20 THEN value_num ELSE NULL END) AS total_protein,
        MAX(CASE WHEN code = '50868' AND value_num <= 10000 THEN value_num ELSE NULL END) AS aniongap,
        MAX(CASE WHEN code = '50882' AND value_num <= 10000 THEN value_num ELSE NULL END) AS bicarbonate,
        MAX(CASE WHEN code = '51006' AND value_num <= 300 THEN value_num ELSE NULL END) AS bun,
        MAX(CASE WHEN code = '50893' AND value_num <= 10000 THEN value_num ELSE NULL END) AS calcium,
        MAX(CASE WHEN code = '50902' AND value_num <= 10000 THEN value_num ELSE NULL END) AS chloride,
        MAX(CASE WHEN code = '50912' AND value_num <= 150 THEN value_num ELSE NULL END) AS creatinine,
        MAX(CASE WHEN code = '50931' AND value_num <= 10000 THEN value_num ELSE NULL END) AS glucose,
        MAX(CASE WHEN code = '50983' AND value_num <= 200 THEN value_num ELSE NULL END) AS sodium,
        MAX(CASE WHEN code = '50971' AND value_num <= 30 THEN value_num ELSE NULL END) AS potassium
    FROM eligible_rows
    GROUP BY specimen_id
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    CAST(albumin AS DOUBLE) AS albumin,
    CAST(globulin AS DOUBLE) AS globulin,
    CAST(total_protein AS DOUBLE) AS total_protein,
    CAST(aniongap AS DOUBLE) AS aniongap,
    CAST(bicarbonate AS DOUBLE) AS bicarbonate,
    CAST(bun AS DOUBLE) AS bun,
    CAST(calcium AS DOUBLE) AS calcium,
    CAST(chloride AS DOUBLE) AS chloride,
    CAST(creatinine AS DOUBLE) AS creatinine,
    CAST(glucose AS DOUBLE) AS glucose,
    CAST(sodium AS DOUBLE) AS sodium,
    CAST(potassium AS DOUBLE) AS potassium
FROM grouped
;
