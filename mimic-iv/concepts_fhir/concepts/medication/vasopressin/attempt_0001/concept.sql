WITH target_medication_administrations AS (
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
      AND ma.item_code = '222315'
), joined_rows AS (
    SELECT
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.rate_unit,
        ma.amount_value,
        e.stay_id_str
    FROM target_medication_administrations ma
    LEFT JOIN encounter_icu e
      ON ma.encounter_key = e.encounter_key
     AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
), typed_rows AS (
    SELECT
        stay_id_str,
        rate_unit,
        CAST(rate_value AS DOUBLE) AS rate_value_double,
        CAST(amount_value AS DOUBLE) AS amount_value_double,
        CASE
            WHEN rate_value IS NULL THEN CAST(NULL AS TIMESTAMP_NTZ)
            ELSE TRY_CAST(effective_period_start AS TIMESTAMP_NTZ)
        END AS starttime_value,
        COALESCE(
            TRY_CAST(effective_period_end AS TIMESTAMP_NTZ),
            TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)
        ) AS endtime_value
    FROM joined_rows
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(NULL AS INTEGER) AS linkorderid,
    CAST(
        CASE
            WHEN rate_unit = 'units/min' THEN rate_value_double * 60.0
            ELSE rate_value_double
        END AS FLOAT
    ) AS vaso_rate,
    CAST(amount_value_double AS FLOAT) AS vaso_amount,
    CAST(starttime_value AS TIMESTAMP_NTZ) AS starttime,
    CAST(endtime_value AS TIMESTAMP_NTZ) AS endtime
FROM typed_rows;
