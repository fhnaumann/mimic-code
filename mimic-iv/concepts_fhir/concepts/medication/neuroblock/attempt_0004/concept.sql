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
    FROM medication_administration AS ma
    WHERE ma.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu'
      AND ma.item_code IN ('222062', '221555')
      AND ma.rate_value IS NOT NULL
), joined_rows AS (
    SELECT
        ma.encounter_key AS icu_encounter_key,
        e.stay_id_str,
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.amount_value
    FROM filtered_rows AS ma
    LEFT JOIN encounter_icu AS e
      ON ma.encounter_key = e.encounter_key
     AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(NULL AS INTEGER) AS orderid,
    CAST(rate_value AS FLOAT) AS drug_rate,
    CAST(amount_value AS FLOAT) AS drug_amount,
    TRY_CAST(effective_period_start AS TIMESTAMP_NTZ) AS starttime,
    TRY_CAST(COALESCE(effective_period_end, effective_datetime) AS TIMESTAMP_NTZ) AS endtime,
    icu_encounter_key
FROM joined_rows;
