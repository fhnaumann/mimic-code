WITH filtered_rows AS (
    SELECT
        ma.patient_key,
        ma.encounter_key,
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.amount_value,
        ma.item_code,
        ma.code_system
    FROM medication_administration AS ma
    WHERE ma.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu'
      AND ma.item_code IN ('222062', '221555')
      AND ma.rate_value IS NOT NULL
), typed_rows AS (
    SELECT
        e.stay_id_str,
        ma.patient_key,
        e.encounter_key AS icu_encounter_key,
        CAST(ma.rate_value AS DOUBLE) AS rate_value_double,
        CAST(ma.amount_value AS DOUBLE) AS amount_value_double,
        TRY_CAST(ma.effective_period_start AS TIMESTAMP_NTZ) AS starttime_value,
        COALESCE(
            TRY_CAST(ma.effective_period_end AS TIMESTAMP_NTZ),
            TRY_CAST(ma.effective_datetime AS TIMESTAMP_NTZ)
        ) AS endtime_value
    FROM filtered_rows AS ma
    LEFT JOIN encounter_icu AS e
      ON ma.encounter_key = e.encounter_key
     AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(NULL AS INTEGER) AS orderid,
    CAST(rate_value_double AS FLOAT) AS drug_rate,
    CAST(amount_value_double AS FLOAT) AS drug_amount,
    CAST(starttime_value AS TIMESTAMP_NTZ) AS starttime,
    CAST(endtime_value AS TIMESTAMP_NTZ) AS endtime,
    icu_encounter_key,
    patient_key
FROM typed_rows;
