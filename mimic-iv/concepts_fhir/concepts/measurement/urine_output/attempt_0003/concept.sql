WITH observation_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        e.icu_encounter_key,
        CAST(e.stay_id_str AS INTEGER) AS stay_id,
        CAST(o.item_code AS INTEGER) AS itemid,
        CAST(o.value_quantity AS DOUBLE) AS value_num,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS charttime
    FROM urine_output_observation o
    INNER JOIN urine_output_encounter e
        ON o.encounter_key = e.icu_encounter_key
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items'
        AND o.item_code IN (
            '226559',
            '226560',
            '226561',
            '226584',
            '226563',
            '226564',
            '226565',
            '226567',
            '226557',
            '226558',
            '227488',
            '227489'
        )
), grouped_rows AS (
    SELECT
        stay_id,
        charttime,
        icu_encounter_key,
        patient_key,
        SUM(
            CASE
                WHEN itemid = 227488 AND value_num > 0 THEN -1 * value_num
                ELSE value_num
            END
        ) AS urineoutput
    FROM observation_rows
    GROUP BY stay_id, charttime, icu_encounter_key, patient_key
)
SELECT
    CAST(stay_id AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(urineoutput AS DOUBLE) AS urineoutput,
    icu_encounter_key,
    patient_key
FROM grouped_rows;
