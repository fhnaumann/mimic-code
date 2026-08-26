WITH observation_rows AS (
    SELECT
        p.subject_id_str,
        o.patient_key,
        e.icu_encounter_key,
        e.stay_id_str,
        o.item_code,
        o.item_system,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS effective_datetime_ntz,
        TRY_CAST(o.effective_period_start AS TIMESTAMP_NTZ) AS effective_period_start_ntz,
        CAST(o.quantity_value AS DOUBLE) AS value_num,
        o.string_value
    FROM vitalsign_observation o
    INNER JOIN vitalsign_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN vitalsign_icu_encounter e
        ON o.icu_encounter_key = e.icu_encounter_key
        AND o.patient_key = e.patient_key
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN (
            '220045', '225309', '225310', '225312', '220050', '220051',
            '220052', '220179', '220180', '220181', '220210', '224690',
            '220277', '225664', '220621', '226537', '223762', '223761',
            '224642'
        )
        AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
        AND p.subject_id_str IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), grouped AS (
    SELECT
        subject_id_str,
        stay_id_str,
        patient_key,
        icu_encounter_key,
        COALESCE(effective_datetime_ntz, effective_period_start_ntz) AS charttime,
        AVG(CASE WHEN item_code IN ('220045')
                AND value_num > 0
                AND value_num < 300
                THEN value_num END) AS heart_rate,
        AVG(CASE WHEN item_code IN ('220179', '220050', '225309')
                AND value_num > 0
                AND value_num < 400
                THEN value_num END) AS sbp,
        AVG(CASE WHEN item_code IN ('220180', '220051', '225310')
                AND value_num > 0
                AND value_num < 300
                THEN value_num END) AS dbp,
        AVG(CASE WHEN item_code IN ('220052', '220181', '225312')
                AND value_num > 0
                AND value_num < 300
                THEN value_num END) AS mbp,
        AVG(CASE WHEN item_code = '220179'
                AND value_num > 0
                AND value_num < 400
                THEN value_num END) AS sbp_ni,
        AVG(CASE WHEN item_code = '220180'
                AND value_num > 0
                AND value_num < 300
                THEN value_num END) AS dbp_ni,
        AVG(CASE WHEN item_code = '220181'
                AND value_num > 0
                AND value_num < 300
                THEN value_num END) AS mbp_ni,
        AVG(CASE WHEN item_code IN ('220210', '224690')
                AND value_num > 0
                AND value_num < 70
                THEN value_num END) AS resp_rate,
        ROUND(CAST(AVG(CASE
                WHEN item_code IN ('223761')
                    AND value_num > 70
                    AND value_num < 120
                    THEN (value_num - 32) / 1.8
                WHEN item_code IN ('223762')
                    AND value_num > 10
                    AND value_num < 50
                    THEN value_num END)
            AS DECIMAL(38, 10)), 2) AS temperature,
        MAX(CASE WHEN item_code = '224642' THEN string_value END)
            AS temperature_site,
        AVG(CASE WHEN item_code IN ('220277')
                AND value_num > 0
                AND value_num <= 100
                THEN value_num END) AS spo2,
        AVG(CASE WHEN item_code IN ('225664', '220621', '226537')
                AND value_num > 0
                THEN value_num END) AS glucose
    FROM observation_rows
    GROUP BY
        subject_id_str,
        stay_id_str,
        patient_key,
        icu_encounter_key,
        COALESCE(effective_datetime_ntz, effective_period_start_ntz)
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(heart_rate AS DOUBLE) AS heart_rate,
    CAST(sbp AS DOUBLE) AS sbp,
    CAST(dbp AS DOUBLE) AS dbp,
    CAST(mbp AS DOUBLE) AS mbp,
    CAST(sbp_ni AS DOUBLE) AS sbp_ni,
    CAST(dbp_ni AS DOUBLE) AS dbp_ni,
    CAST(mbp_ni AS DOUBLE) AS mbp_ni,
    CAST(resp_rate AS DOUBLE) AS resp_rate,
    CAST(temperature AS DECIMAL(38, 2)) AS temperature,
    CAST(temperature_site AS VARCHAR(255)) AS temperature_site,
    CAST(spo2 AS DOUBLE) AS spo2,
    CAST(glucose AS DOUBLE) AS glucose,
    patient_key AS patient_key,
    icu_encounter_key AS icu_encounter_key
FROM grouped
;
