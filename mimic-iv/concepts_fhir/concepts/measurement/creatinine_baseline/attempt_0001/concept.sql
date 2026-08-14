WITH p AS (
    SELECT
        CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
        CASE
            WHEN pt.gender_fhir = 'female' THEN 'F'
            WHEN pt.gender_fhir = 'male' THEN 'M'
            ELSE NULL
        END AS gender,
        CAST(
            YEAR(TRY_CAST(e.period_start AS TIMESTAMP_NTZ))
            - YEAR(TRY_CAST(pt.birth_date AS TIMESTAMP_NTZ))
            AS BIGINT
        ) AS age,
        CASE WHEN pt.gender_fhir = 'female' THEN
            POWER(
                75.0 / 186.0 / POWER(
                    YEAR(TRY_CAST(e.period_start AS TIMESTAMP_NTZ))
                    - YEAR(TRY_CAST(pt.birth_date AS TIMESTAMP_NTZ)),
                    -0.203
                ) / 0.742,
                -1 / 1.154
            )
            ELSE
            POWER(
                75.0 / 186.0 / POWER(
                    YEAR(TRY_CAST(e.period_start AS TIMESTAMP_NTZ))
                    - YEAR(TRY_CAST(pt.birth_date AS TIMESTAMP_NTZ)),
                    -0.203
                ),
                -1 / 1.154
            )
        END AS mdrd_est
    FROM encounter e
    LEFT JOIN patient pt
        ON e.patient_key = pt.patient_key
    WHERE e.hadm_id_str IS NOT NULL
        AND YEAR(TRY_CAST(e.period_start AS TIMESTAMP_NTZ))
            - YEAR(TRY_CAST(pt.birth_date AS TIMESTAMP_NTZ)) >= 18
), creatinine_rows AS (
    SELECT
        CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
        CAST(s.specimen_id_str AS INTEGER) AS specimen_id,
        CAST(o.quantity_value AS DOUBLE) AS creatinine_value
    FROM observation o
    INNER JOIN specimen s
        ON o.specimen_key = s.specimen_key
    LEFT JOIN encounter e
        ON o.encounter_key = e.encounter_key
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems'
        AND o.item_code = '50912'
        AND o.quantity_value IS NOT NULL
        AND o.quantity_comparator IS NULL
        AND o.value_string IS NULL
), chemistry_by_specimen AS (
    SELECT
        MAX(hadm_id) AS hadm_id,
        specimen_id,
        MAX(creatinine_value) AS creatinine
    FROM creatinine_rows
    WHERE creatinine_value > 0
        AND creatinine_value <= 150
    GROUP BY specimen_id
), lab AS (
    SELECT
        hadm_id,
        MIN(creatinine) AS scr_min
    FROM chemistry_by_specimen
    GROUP BY hadm_id
), ckd AS (
    SELECT
        CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
        MAX(1) AS ckd_flag
    FROM condition c
    LEFT JOIN encounter e
        ON c.encounter_key = e.encounter_key
    WHERE e.hadm_id_str IS NOT NULL
        AND (
            (
                c.diagnosis_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9'
                AND SUBSTR(c.diagnosis_code, 1, 3) = '585'
            )
            OR (
                c.diagnosis_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
                AND SUBSTR(c.diagnosis_code, 1, 3) = 'N18'
            )
        )
    GROUP BY CAST(e.hadm_id_str AS INTEGER)
)
SELECT
    CAST(p.hadm_id AS INTEGER) AS hadm_id,
    CAST(p.gender AS VARCHAR(255)) AS gender,
    CAST(p.age AS BIGINT) AS age,
    CAST(lab.scr_min AS DOUBLE) AS scr_min,
    CAST(COALESCE(ckd.ckd_flag, 0) AS INTEGER) AS ckd,
    CAST(p.mdrd_est AS DOUBLE) AS mdrd_est,
    CAST(
        CASE
            WHEN lab.scr_min <= 1.1 THEN lab.scr_min
            WHEN ckd.ckd_flag = 1 THEN lab.scr_min
            ELSE p.mdrd_est
        END
        AS DOUBLE
    ) AS scr_baseline
FROM p
LEFT JOIN lab
    ON p.hadm_id = lab.hadm_id
LEFT JOIN ckd
    ON p.hadm_id = ckd.hadm_id
;
