WITH target_medication_administrations AS (
    SELECT
        ma.encounter_key,
        ma.patient_key,
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.amount_value,
        ma.item_code,
        ma.code_system
    FROM medication_administration AS ma
    WHERE ma.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu'
      AND ma.item_code = '221986'
), joined_rows AS (
    SELECT
        e.encounter_key AS icu_encounter_key,
        ma.patient_key,
        e.stay_id_str,
        TRY_CAST(ma.effective_period_start AS TIMESTAMP_NTZ) AS starttime_value,
        COALESCE(
            TRY_CAST(ma.effective_period_end AS TIMESTAMP_NTZ),
            TRY_CAST(ma.effective_datetime AS TIMESTAMP_NTZ)
        ) AS endtime_value,
        CAST(ma.rate_value AS DOUBLE) AS rate_value,
        CAST(ma.amount_value AS DOUBLE) AS amount_value
    FROM target_medication_administrations AS ma
    LEFT JOIN encounter_icu AS e
      ON ma.encounter_key = e.encounter_key
     AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(NULL AS INTEGER) AS linkorderid,
    CAST(rate_value AS FLOAT) AS vaso_rate,
    CAST(amount_value AS FLOAT) AS vaso_amount,
    CAST(starttime_value AS TIMESTAMP_NTZ) AS starttime,
    CAST(endtime_value AS TIMESTAMP_NTZ) AS endtime,
    icu_encounter_key,
    patient_key
FROM joined_rows;
