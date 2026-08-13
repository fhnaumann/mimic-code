WITH target_medication_administrations AS (
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
        AND ma.item_code = '221662'
), joined_rows AS (
    SELECT
        ma.effective_datetime,
        ma.effective_period_start,
        ma.effective_period_end,
        ma.rate_value,
        ma.amount_value,
        e.stay_id_str
    FROM target_medication_administrations ma
    LEFT JOIN encounter_icu e
        ON ma.encounter_key = e.encounter_key
        AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(NULL AS INTEGER) AS linkorderid,
    CAST(rate_value AS FLOAT) AS vaso_rate,
    CAST(amount_value AS FLOAT) AS vaso_amount,
    TRY_CAST(effective_period_start AS TIMESTAMP_NTZ) AS starttime,
    COALESCE(
        TRY_CAST(effective_period_end AS TIMESTAMP_NTZ),
        TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)
    ) AS endtime
FROM joined_rows
;
