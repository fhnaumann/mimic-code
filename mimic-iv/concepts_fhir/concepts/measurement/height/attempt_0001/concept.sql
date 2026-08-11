WITH observation_rows AS (
    SELECT
        p.subject_id_str,
        e.stay_id_str,
        o.item_code,
        o.item_system,
        CAST(o.quantity_value AS DOUBLE) AS value_num,
        CAST(
            TRY_TO_TIMESTAMP(
                REGEXP_REPLACE(
                    o.effective_datetime,
                    '(Z|[+-][0-9]{2}:[0-9]{2})$',
                    ''
                ),
                "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
            ) AS TIMESTAMP_NTZ
        ) AS effective_datetime_ntz,
        CAST(
            TRY_TO_TIMESTAMP(
                REGEXP_REPLACE(
                    o.effective_period_start,
                    '(Z|[+-][0-9]{2}:[0-9]{2})$',
                    ''
                ),
                "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
            ) AS TIMESTAMP_NTZ
        ) AS effective_period_start_ntz
    FROM height_observation o
    INNER JOIN height_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN height_encounter e
        ON o.encounter_key = e.encounter_key
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('226707', '226730')
        AND o.quantity_value IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), typed_rows AS (
    SELECT
        subject_id_str,
        stay_id_str,
        item_code,
        value_num,
        COALESCE(effective_datetime_ntz, effective_period_start_ntz) AS charttime
    FROM observation_rows
), ht_in AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        ROUND(value_num * 2.54, 2) AS height
    FROM typed_rows
    WHERE item_code = '226707'
), ht_cm AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        ROUND(value_num, 2) AS height
    FROM typed_rows
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
