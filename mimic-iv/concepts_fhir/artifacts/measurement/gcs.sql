-- Chartevents Observation.id is generated from the pre-TIMESTAMPTZ source
-- charttime and source value, while effectiveDateTime contains the possibly
-- normalized served time. Enumerate the finite GCS (itemid, value) vocabulary
-- and match UUIDv5 candidates at both served time and one hour earlier. The
-- earlier time is used only when its UUID is the witness; genuine 03:xx rows
-- therefore remain at their served time. The same witness identifies the exact
-- No Response-ETT source value; Quantity.value = 1 is not used.
WITH gcs_vocabulary AS (
    SELECT * FROM VALUES
        ('220739', 'None'),
        ('220739', 'Spontaneously'),
        ('220739', 'To Pain'),
        ('220739', 'To Speech'),
        ('223900', 'Confused'),
        ('223900', 'Inappropriate Words'),
        ('223900', 'Incomprehensible sounds'),
        ('223900', 'No Response'),
        ('223900', 'No Response-ETT'),
        ('223900', 'Oriented'),
        ('223901', 'Abnormal Flexion'),
        ('223901', 'Abnormal extension'),
        ('223901', 'Flex-withdraws'),
        ('223901', 'Localizes Pain'),
        ('223901', 'No response'),
        ('223901', 'Obeys Commands')
    AS v(item_code, source_value)
), observation_rows AS (
    SELECT
        o.observation_key,
        o.encounter_key,
        o.patient_key,
        o.item_code,
        o.code_system,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS fhir_charttime,
        CAST(o.quantity_value AS DOUBLE) AS quantity_value
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
), candidate_times AS (
    SELECT
        i.*,
        i.fhir_charttime AS candidate_charttime,
        0 AS hours_back
    FROM identified_rows i
    UNION ALL
    SELECT
        i.*,
        i.fhir_charttime - INTERVAL 1 HOUR AS candidate_charttime,
        1 AS hours_back
    FROM identified_rows i
), uuid_digests AS (
    SELECT
        c.*,
        v.source_value,
        SHA1(
            CONCAT(
                UNHEX('36e18860b4aa5577bc80a5b07922cd3d'),
                ENCODE(
                    CONCAT(
                        c.stay_id_str,
                        '-',
                        CAST(c.candidate_charttime AS STRING),
                        '-',
                        c.item_code,
                        '-',
                        v.source_value
                    ),
                    'UTF-8'
                )
            )
        ) AS uuid_digest
    FROM candidate_times c
    INNER JOIN gcs_vocabulary v
        ON c.item_code = v.item_code
), uuid_candidates AS (
    SELECT
        d.*,
        CONCAT(
            'Observation/',
            LOWER(
                CONCAT(
                    SUBSTR(d.uuid_digest, 1, 8),
                    '-',
                    SUBSTR(d.uuid_digest, 9, 4),
                    '-',
                    '5',
                    SUBSTR(d.uuid_digest, 14, 3),
                    '-',
                    CASE LOWER(SUBSTR(d.uuid_digest, 17, 1))
                        WHEN '0' THEN '8'
                        WHEN '1' THEN '9'
                        WHEN '2' THEN 'a'
                        WHEN '3' THEN 'b'
                        WHEN '4' THEN '8'
                        WHEN '5' THEN '9'
                        WHEN '6' THEN 'a'
                        WHEN '7' THEN 'b'
                        WHEN '8' THEN '8'
                        WHEN '9' THEN '9'
                        WHEN 'a' THEN 'a'
                        WHEN 'b' THEN 'b'
                        WHEN 'c' THEN '8'
                        WHEN 'd' THEN '9'
                        WHEN 'e' THEN 'a'
                        WHEN 'f' THEN 'b'
                    END,
                    SUBSTR(d.uuid_digest, 18, 3),
                    '-',
                    SUBSTR(d.uuid_digest, 21, 12)
                )
            )
        ) AS candidate_observation_key
    FROM uuid_digests d
), recovered_rows AS (
    SELECT
        u.observation_key,
        u.subject_id_str,
        u.stay_id_str,
        u.item_code,
        u.quantity_value,
        u.fhir_charttime,
        MAX(
            CASE
                WHEN u.hours_back = 0
                    AND u.candidate_observation_key = u.observation_key
                    THEN 1
                ELSE 0
            END
        ) AS current_match,
        MAX(
            CASE
                WHEN u.hours_back = 1
                    AND u.candidate_observation_key = u.observation_key
                    THEN 1
                ELSE 0
            END
        ) AS earlier_match,
        MAX(
            CASE
                WHEN u.candidate_observation_key = u.observation_key
                    AND u.source_value = 'No Response-ETT'
                    THEN 1
                ELSE 0
            END
        ) AS is_ett
    FROM uuid_candidates u
    GROUP BY
        u.observation_key,
        u.subject_id_str,
        u.stay_id_str,
        u.item_code,
        u.quantity_value,
        u.fhir_charttime
), typed_rows AS (
    SELECT
        r.subject_id_str,
        r.stay_id_str,
        CASE
            WHEN r.current_match = 1 THEN r.fhir_charttime
            WHEN r.earlier_match = 1 THEN r.fhir_charttime - INTERVAL 1 HOUR
            ELSE r.fhir_charttime
        END AS charttime,
        r.item_code,
        r.quantity_value,
        r.is_ett
    FROM recovered_rows r
), pivoted AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        MAX(
            CASE WHEN item_code = '223901' THEN quantity_value ELSE NULL END
        ) AS gcsmotor,
        MAX(
            CASE
                WHEN item_code = '223900' AND is_ett = 1 THEN CAST(0 AS DOUBLE)
                WHEN item_code = '223900' THEN quantity_value
                ELSE NULL
            END
        ) AS gcsverbal,
        MAX(
            CASE WHEN item_code = '220739' THEN quantity_value ELSE NULL END
        ) AS gcseyes,
        MAX(
            CASE
                WHEN item_code = '223900' AND is_ett = 1 THEN 1
                ELSE 0
            END
        ) AS endotrachflag
    FROM typed_rows
    GROUP BY subject_id_str, stay_id_str, charttime
), base AS (
    SELECT
        p.*,
        ROW_NUMBER() OVER (
            PARTITION BY p.stay_id_str
            ORDER BY p.charttime ASC
        ) AS rn
    FROM pivoted p
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
