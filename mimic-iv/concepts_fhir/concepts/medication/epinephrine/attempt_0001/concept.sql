WITH filtered_rows AS (
    SELECT
        ma.encounter_key,
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.amount_value,
        ma.item_code,
        ma.code_system
    FROM medication_administration ma
    WHERE ma.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu'
      AND ma.item_code = '221289'
), typed_rows AS (
    SELECT
        e.stay_id_str,
        CAST(
            TRY_TO_TIMESTAMP(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(ma.effective_period_start, 'T', ' '),
                    '(Z|[+-][0-9]{2}:[0-9]{2})$',
                    ''
                ),
                'yyyy-MM-dd HH:mm:ss[.SSSSSS]'
            ) AS TIMESTAMP_NTZ
        ) AS effective_period_start_ntz,
        CAST(
            TRY_TO_TIMESTAMP(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(ma.effective_period_end, 'T', ' '),
                    '(Z|[+-][0-9]{2}:[0-9]{2})$',
                    ''
                ),
                'yyyy-MM-dd HH:mm:ss[.SSSSSS]'
            ) AS TIMESTAMP_NTZ
        ) AS effective_period_end_ntz,
        CAST(
            TRY_TO_TIMESTAMP(
                REGEXP_REPLACE(
                    REGEXP_REPLACE(ma.effective_datetime, 'T', ' '),
                    '(Z|[+-][0-9]{2}:[0-9]{2})$',
                    ''
                ),
                'yyyy-MM-dd HH:mm:ss[.SSSSSS]'
            ) AS TIMESTAMP_NTZ
        ) AS effective_datetime_ntz,
        CAST(ma.rate_value AS DOUBLE) AS rate_value,
        CAST(ma.amount_value AS DOUBLE) AS amount_value
    FROM filtered_rows ma
    LEFT JOIN encounter_icu e
      ON ma.encounter_key = e.encounter_key
     AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(NULL AS INTEGER) AS linkorderid,
    CAST(rate_value AS FLOAT) AS vaso_rate,
    CAST(amount_value AS FLOAT) AS vaso_amount,
    CAST(effective_period_start_ntz AS TIMESTAMP_NTZ) AS starttime,
    CAST(COALESCE(effective_period_end_ntz, effective_datetime_ntz) AS TIMESTAMP_NTZ) AS endtime
FROM typed_rows;
