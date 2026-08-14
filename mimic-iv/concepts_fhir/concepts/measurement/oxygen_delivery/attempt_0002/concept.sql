WITH observation_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        o.code,
        o.system,
        TRY_CAST(
            COALESCE(o.effective_datetime, o.effective_period_start)
            AS TIMESTAMP_NTZ
        ) AS charttime,
        CAST(o.quantity_value AS DOUBLE) AS valuenum,
        o.string_value AS value,
        o.issued
    FROM oxygen_delivery_observation o
    WHERE o.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.code IN ('223834', '227582', '227287', '226732')
), identified_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        p.subject_id_str,
        e.stay_id_str,
        o.code,
        o.system,
        o.charttime,
        o.valuenum,
        o.value,
        o.issued
    FROM observation_rows o
    INNER JOIN oxygen_delivery_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN oxygen_delivery_encounter e
        ON o.encounter_key = e.encounter_key
), flow_stg1 AS (
    SELECT
        patient_key,
        encounter_key,
        subject_id_str,
        stay_id_str,
        charttime,
        CASE
            WHEN code IN ('223834', '227582') THEN '223834'
            ELSE code
        END AS item_code,
        value,
        valuenum,
        issued
    FROM identified_rows
    WHERE code IN ('223834', '227582', '227287')
        AND (valuenum IS NOT NULL OR value IS NOT NULL)
), flow_stg2 AS (
    SELECT
        f.*,
        ROW_NUMBER() OVER (
            PARTITION BY patient_key, charttime, item_code
            ORDER BY issued DESC, valuenum DESC
        ) AS rn
    FROM flow_stg1 f
), flow_selected AS (
    SELECT
        patient_key,
        encounter_key,
        subject_id_str,
        stay_id_str,
        charttime,
        item_code,
        valuenum
    FROM flow_stg2
    WHERE rn = 1
), device_ranked AS (
    SELECT
        patient_key,
        charttime,
        code,
        value AS o2_device,
        ROW_NUMBER() OVER (
            PARTITION BY patient_key, charttime, code
            ORDER BY issued DESC NULLS LAST, value DESC NULLS LAST
        ) AS rn
    FROM identified_rows
    WHERE code = '226732'
), stg AS (
    SELECT
        f.subject_id_str,
        f.stay_id_str,
        f.charttime,
        f.item_code,
        f.valuenum,
        d.o2_device,
        d.rn
    FROM flow_selected f
    LEFT JOIN device_ranked d
        ON f.patient_key = d.patient_key
        AND f.charttime = d.charttime
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(MAX(CAST(stay_id_str AS INTEGER)) AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(MAX(CASE WHEN item_code = '223834' THEN valuenum ELSE NULL END) AS FLOAT) AS o2_flow,
    CAST(MAX(CASE WHEN item_code = '227287' THEN valuenum ELSE NULL END) AS FLOAT) AS o2_flow_additional,
    CAST(MAX(CASE WHEN rn = 1 THEN o2_device ELSE NULL END) AS VARCHAR(255)) AS o2_delivery_device_1,
    CAST(MAX(CASE WHEN rn = 2 THEN o2_device ELSE NULL END) AS VARCHAR(255)) AS o2_delivery_device_2,
    CAST(MAX(CASE WHEN rn = 3 THEN o2_device ELSE NULL END) AS VARCHAR(255)) AS o2_delivery_device_3,
    CAST(MAX(CASE WHEN rn = 4 THEN o2_device ELSE NULL END) AS VARCHAR(255)) AS o2_delivery_device_4
FROM stg
GROUP BY subject_id_str, charttime
;
