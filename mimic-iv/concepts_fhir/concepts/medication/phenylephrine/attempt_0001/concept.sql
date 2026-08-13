WITH filtered_rows AS (
    SELECT
        ma.encounter_key,
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.rate_unit,
        ma.amount_value,
        ma.item_code,
        ma.code_system
    FROM medication_administration ma
    WHERE ma.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu'
      AND ma.item_code = '221749'
), joined_rows AS (
    SELECT
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.rate_unit,
        ma.amount_value,
        e.stay_id_str
    FROM filtered_rows ma
    LEFT JOIN encounter_icu e
        ON ma.encounter_key = e.encounter_key
       AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
), typed_rows AS (
    SELECT
        stay_id_str,
        rate_unit,
        CAST(rate_value AS DOUBLE) AS rate_value_double,
        CAST(amount_value AS DOUBLE) AS amount_value_double,
        TRY_CAST(effective_datetime AS TIMESTAMP_NTZ) AS effective_datetime_ntz,
        TRY_CAST(effective_period_start AS TIMESTAMP_NTZ) AS effective_period_start_ntz,
        TRY_CAST(effective_period_end AS TIMESTAMP_NTZ) AS effective_period_end_ntz
    FROM joined_rows
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(NULL AS INTEGER) AS linkorderid,
    CAST(rate_value_double AS FLOAT) AS vaso_rate,
    CAST(amount_value_double AS FLOAT) AS vaso_amount,
    CAST(effective_period_start_ntz AS TIMESTAMP_NTZ) AS starttime,
    CAST(COALESCE(effective_period_end_ntz, effective_datetime_ntz) AS TIMESTAMP_NTZ) AS endtime
FROM typed_rows
;
