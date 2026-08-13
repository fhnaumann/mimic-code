WITH observation_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        p.subject_id_str,
        e.stay_id_str,
        o.item_code,
        o.item_system,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS charttime,
        CAST(o.quantity_value AS DOUBLE) AS value_num
    FROM height_observation o
    INNER JOIN height_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN height_encounter e
        ON o.encounter_key = e.encounter_key
        AND o.patient_key = e.patient_key
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('226707', '226730')
        AND o.quantity_value IS NOT NULL
        AND p.subject_id_str IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), ht_in AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        ROUND(value_num * 2.54, 2) AS height
    FROM observation_rows
    WHERE item_code = '226707'
), ht_cm AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        ROUND(value_num, 2) AS height
    FROM observation_rows
    WHERE item_code = '226730'
), ht_stg0 AS (
    SELECT
        COALESCE(h1.subject_id_str, h2.subject_id_str) AS subject_id_str,
        COALESCE(h1.stay_id_str, h2.stay_id_str) AS stay_id_str,
        COALESCE(h1.charttime, h2.charttime) AS charttime,
        COALESCE(h1.height, h2.height) AS height
    FROM ht_cm h1
    FULL OUTER JOIN ht_in h2
        ON h1.subject_id_str = h2.subject_id_str
        AND h1.charttime = h2.charttime
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(height AS DECIMAL(38,2)) AS height
FROM ht_stg0
WHERE height IS NOT NULL
    AND height > 120
    AND height < 230
;
