WITH observation_rows AS (
    SELECT
        p.subject_id_str,
        p.patient_key,
        e.icu_encounter_key,
        e.stay_id_str,
        o.item_code,
        o.item_system,
        o.component_code,
        o.component_system,
        o.component_text,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS charttime,
        CAST(o.quantity_value AS DOUBLE) AS quantity_num
    FROM gcs_observation o
    INNER JOIN gcs_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN gcs_encounter e
        ON o.icu_encounter_key = e.icu_encounter_key
        AND o.patient_key = e.patient_key
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('223900', '223901', '220739')
        AND p.subject_id_str IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), base AS (
    SELECT
        subject_id_str,
        stay_id_str,
        patient_key,
        icu_encounter_key,
        charttime,
        MAX(
            CASE WHEN item_code = '223901' THEN quantity_num ELSE NULL END
        ) AS gcsmotor,
        MAX(
            CASE
                WHEN item_code = '223900'
                    AND component_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
                    AND component_code = '223900'
                    AND component_text = 'No Response-ETT'
                    THEN CAST(0 AS DOUBLE)
                WHEN item_code = '223900' THEN quantity_num
                ELSE NULL
            END
        ) AS gcsverbal,
        MAX(
            CASE WHEN item_code = '220739' THEN quantity_num ELSE NULL END
        ) AS gcseyes,
        MAX(
            CASE
                WHEN item_code = '223900'
                    AND component_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
                    AND component_code = '223900'
                    AND component_text = 'No Response-ETT'
                    THEN 1
                ELSE 0
            END
        ) AS endotrachflag,
        ROW_NUMBER() OVER (
            PARTITION BY stay_id_str
            ORDER BY charttime ASC
        ) AS rn
    FROM observation_rows
    GROUP BY
        subject_id_str,
        stay_id_str,
        patient_key,
        icu_encounter_key,
        charttime
), gcs AS (
    SELECT
        b.subject_id_str,
        b.stay_id_str,
        b.patient_key,
        b.icu_encounter_key,
        b.charttime,
        b.gcsmotor,
        b.gcsverbal,
        b.gcseyes,
        b.endotrachflag,
        b2.gcsverbal AS gcsverbalprev,
        b2.gcsmotor AS gcsmotorprev,
        b2.gcseyes AS gcseyesprev,
        CASE
            WHEN b.gcsverbal = 0
                THEN 15
            WHEN b.gcsverbal IS NULL AND b2.gcsverbal = 0
                THEN 15
            WHEN b2.gcsverbal = 0
                THEN
                    COALESCE(b.gcsmotor, 6)
                    + COALESCE(b.gcsverbal, 5)
                    + COALESCE(b.gcseyes, 4)
            ELSE
                COALESCE(b.gcsmotor, COALESCE(b2.gcsmotor, 6))
                + COALESCE(b.gcsverbal, COALESCE(b2.gcsverbal, 5))
                + COALESCE(b.gcseyes, COALESCE(b2.gcseyes, 4))
        END AS gcs
    FROM base b
    LEFT JOIN base b2
        ON b.stay_id_str = b2.stay_id_str
        AND b.rn = b2.rn + 1
        AND b2.charttime > b.charttime - INTERVAL 6 HOURS
), gcs_stg AS (
    SELECT
        subject_id_str,
        stay_id_str,
        patient_key,
        icu_encounter_key,
        charttime,
        gcs,
        COALESCE(gcsmotor, gcsmotorprev) AS gcsmotor,
        COALESCE(gcsverbal, gcsverbalprev) AS gcsverbal,
        COALESCE(gcseyes, gcseyesprev) AS gcseyes,
        endotrachflag
    FROM gcs
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(gcs AS FLOAT) AS gcs,
    CAST(gcsmotor AS FLOAT) AS gcs_motor,
    CAST(gcsverbal AS FLOAT) AS gcs_verbal,
    CAST(gcseyes AS FLOAT) AS gcs_eyes,
    CAST(endotrachflag AS INTEGER) AS gcs_unable,
    patient_key AS patient_key,
    icu_encounter_key AS icu_encounter_key
FROM gcs_stg
;
