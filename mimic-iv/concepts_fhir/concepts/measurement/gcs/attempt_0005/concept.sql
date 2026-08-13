-- Direct FHIR port of the canonical GCS pivot and six-hour carry-forward.
-- The chartevents ETL writes numeric rows as Quantity and discards their
-- source value text.  Consequently Quantity 1 is intentionally retained as
-- the served verbal value: it is not used as a No Response-ETT heuristic.
-- If an exact source label is present in valueString, it is used directly;
-- the probed GCS numeric rows have no such FHIR valueString.  The resulting
-- loss of the No Response-ETT branch is essential to GCS and is left visible
-- for the equivalence judge rather than reconstructed through resource ids.
WITH observation_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS charttime,
        CAST(o.quantity_value AS DOUBLE) AS quantity_value,
        o.value_string,
        o.item_code,
        o.code_system
    FROM gcs_observation o
    WHERE o.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('223900', '223901', '220739')
), identified_rows AS (
    SELECT
        o.*,
        p.subject_id_str,
        e.stay_id_str
    FROM observation_rows o
    INNER JOIN gcs_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN gcs_encounter e
        ON o.encounter_key = e.encounter_key
    WHERE p.subject_id_str IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), base AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        MAX(
            CASE WHEN item_code = '223901' THEN quantity_value ELSE NULL END
        ) AS gcsmotor,
        MAX(
            CASE
                WHEN item_code = '223900'
                    AND value_string = 'No Response-ETT'
                    THEN CAST(0 AS DOUBLE)
                WHEN item_code = '223900' THEN quantity_value
                ELSE NULL
            END
        ) AS gcsverbal,
        MAX(
            CASE WHEN item_code = '220739' THEN quantity_value ELSE NULL END
        ) AS gcseyes,
        MAX(
            CASE
                WHEN item_code = '223900'
                    AND value_string = 'No Response-ETT'
                    THEN 1
                ELSE 0
            END
        ) AS endotrachflag,
        ROW_NUMBER() OVER (
            PARTITION BY stay_id_str
            ORDER BY charttime ASC
        ) AS rn
    FROM identified_rows
    GROUP BY subject_id_str, stay_id_str, charttime
), gcs AS (
    SELECT
        b.*,
        b2.gcsverbal AS gcsverbalprev,
        b2.gcsmotor AS gcsmotorprev,
        b2.gcseyes AS gcseyesprev,
        CASE
            WHEN b.gcsverbal = 0 THEN 15
            WHEN b.gcsverbal IS NULL AND b2.gcsverbal = 0 THEN 15
            WHEN b2.gcsverbal = 0 THEN
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
        charttime,
        gcs,
        COALESCE(gcsmotor, gcsmotorprev) AS gcsmotor,
        COALESCE(gcsverbal, gcsverbalprev) AS gcsverbal,
        COALESCE(gcseyes, gcseyesprev) AS gcseyes,
        CASE WHEN COALESCE(gcsmotor, gcsmotorprev) IS NULL THEN 0 ELSE 1 END
            + CASE WHEN COALESCE(gcsverbal, gcsverbalprev) IS NULL THEN 0 ELSE 1 END
            + CASE WHEN COALESCE(gcseyes, gcseyesprev) IS NULL THEN 0 ELSE 1 END
            AS components_measured,
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
    CAST(endotrachflag AS INTEGER) AS gcs_unable
FROM gcs_stg
;
