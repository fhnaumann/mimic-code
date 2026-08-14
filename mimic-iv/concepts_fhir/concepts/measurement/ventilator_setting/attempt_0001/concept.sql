WITH observation_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        o.item_code,
        o.item_system,
        COALESCE(
            TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ),
            TRY_CAST(o.effective_period_start AS TIMESTAMP_NTZ)
        ) AS charttime,
        CAST(o.quantity_value AS DOUBLE) AS source_valuenum,
        o.value_string
    FROM ventilator_setting_observation o
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN (
            '224688', '224689', '224690', '224687', '224685', '224684',
            '224686', '224696', '220339', '224700', '223835', '223849',
            '229314', '223848', '224691'
        )
        AND (o.quantity_value IS NOT NULL OR o.value_string IS NOT NULL)
), identified_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        o.item_code,
        o.item_system,
        o.charttime,
        o.source_valuenum,
        o.value_string,
        p.subject_id_str,
        e.stay_id_str
    FROM observation_rows o
    INNER JOIN ventilator_setting_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN ventilator_setting_encounter e
        ON o.encounter_key = e.encounter_key
    WHERE p.subject_id_str IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), cleaned_rows AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        item_code,
        value_string,
        CASE
            WHEN item_code = '223835' THEN
                CASE
                    WHEN source_valuenum >= 0.20 AND source_valuenum <= 1
                        THEN source_valuenum * 100
                    WHEN source_valuenum > 1 AND source_valuenum < 20
                        THEN NULL
                    WHEN source_valuenum >= 20 AND source_valuenum <= 100
                        THEN source_valuenum
                    ELSE NULL
                END
            WHEN item_code IN ('220339', '224700') THEN
                CASE
                    WHEN source_valuenum > 100 THEN NULL
                    WHEN source_valuenum < 0 THEN NULL
                    ELSE source_valuenum
                END
            ELSE source_valuenum
        END AS valuenum
    FROM identified_rows
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(MAX(CAST(stay_id_str AS INTEGER)) AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(MAX(CASE WHEN item_code = '224688' THEN valuenum ELSE NULL END) AS FLOAT) AS respiratory_rate_set,
    CAST(MAX(CASE WHEN item_code = '224690' THEN valuenum ELSE NULL END) AS FLOAT) AS respiratory_rate_total,
    CAST(MAX(CASE WHEN item_code = '224689' THEN valuenum ELSE NULL END) AS FLOAT) AS respiratory_rate_spontaneous,
    CAST(MAX(CASE WHEN item_code = '224687' THEN valuenum ELSE NULL END) AS FLOAT) AS minute_volume,
    CAST(MAX(CASE WHEN item_code = '224684' THEN valuenum ELSE NULL END) AS FLOAT) AS tidal_volume_set,
    CAST(MAX(CASE WHEN item_code = '224685' THEN valuenum ELSE NULL END) AS FLOAT) AS tidal_volume_observed,
    CAST(MAX(CASE WHEN item_code = '224686' THEN valuenum ELSE NULL END) AS FLOAT) AS tidal_volume_spontaneous,
    CAST(MAX(CASE WHEN item_code = '224696' THEN valuenum ELSE NULL END) AS FLOAT) AS plateau_pressure,
    CAST(MAX(CASE WHEN item_code IN ('220339', '224700') THEN valuenum ELSE NULL END) AS FLOAT) AS peep,
    CAST(MAX(CASE WHEN item_code = '223835' THEN valuenum ELSE NULL END) AS FLOAT) AS fio2,
    CAST(MAX(CASE WHEN item_code = '224691' THEN valuenum ELSE NULL END) AS FLOAT) AS flow_rate,
    CAST(MAX(CASE WHEN item_code = '223849' THEN value_string ELSE NULL END) AS VARCHAR(255)) AS ventilator_mode,
    CAST(MAX(CASE WHEN item_code = '229314' THEN value_string ELSE NULL END) AS VARCHAR(255)) AS ventilator_mode_hamilton,
    CAST(MAX(CASE WHEN item_code = '223848' THEN value_string ELSE NULL END) AS VARCHAR(255)) AS ventilator_type
FROM cleaned_rows
GROUP BY subject_id_str, charttime
;
