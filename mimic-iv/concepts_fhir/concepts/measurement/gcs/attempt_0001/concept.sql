-- The chartevents ETL writes numeric rows as valueQuantity and discards the
-- source text.  In particular, Quantity.value = 1 is shared by No Response
-- and No Response-ETT, so it is never used as the ETT discriminator here.
-- Instead, the ETL's UUIDv5 input (fhir_observation_chartevents.sql:21) is an
-- exact witness for the source value 'No Response-ETT'.  The second candidate
-- name covers the ETL's one-hour DST-gap normalization of charttime.
WITH observation_rows AS (
    SELECT
        o.observation_key,
        o.encounter_key,
        o.patient_key,
        o.item_code,
        o.code_system,
        CAST(
            TRY_TO_TIMESTAMP(
                REGEXP_REPLACE(
                    o.effective_datetime,
                    '(Z|[+-][0-9]{2}:[0-9]{2})$',
                    ''
                ),
                "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
            ) AS TIMESTAMP_NTZ
        ) AS charttime,
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
), uuid_names AS (
    SELECT
        i.*,
        CONCAT(
            i.stay_id_str, '-', CAST(i.charttime AS STRING),
            '-223900-No Response-ETT'
        ) AS current_ett_name,
        CONCAT(
            i.stay_id_str, '-', CAST(i.charttime - INTERVAL 1 HOUR AS STRING),
            '-223900-No Response-ETT'
        ) AS prior_ett_name
    FROM identified_rows i
), uuid_digests AS (
    SELECT
        n.*,
        SHA1(
            CONCAT(
                UNHEX('36e18860b4aa5577bc80a5b07922cd3d'),
                ENCODE(n.current_ett_name, 'UTF-8')
            )
        ) AS current_ett_digest,
        SHA1(
            CONCAT(
                UNHEX('36e18860b4aa5577bc80a5b07922cd3d'),
                ENCODE(n.prior_ett_name, 'UTF-8')
            )
        ) AS prior_ett_digest
    FROM uuid_names n
), uuid_forms AS (
    SELECT
        d.*,
        CONCAT(
            SUBSTR(d.current_ett_digest, 1, 12),
            '5',
            SUBSTR(d.current_ett_digest, 14, 3),
            CASE LOWER(SUBSTR(d.current_ett_digest, 17, 1))
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
            SUBSTR(d.current_ett_digest, 18)
        ) AS current_ett_uuid_hex,
        CONCAT(
            SUBSTR(d.prior_ett_digest, 1, 12),
            '5',
            SUBSTR(d.prior_ett_digest, 14, 3),
            CASE LOWER(SUBSTR(d.prior_ett_digest, 17, 1))
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
            SUBSTR(d.prior_ett_digest, 18)
        ) AS prior_ett_uuid_hex
    FROM uuid_digests d
), typed_rows AS (
    SELECT
        u.subject_id_str,
        u.stay_id_str,
        u.charttime,
        u.item_code,
        u.quantity_value,
        CASE
            WHEN u.item_code = '223900'
                AND u.observation_key = CONCAT(
                    'Observation/',
                    LOWER(CONCAT(
                        SUBSTR(u.current_ett_uuid_hex, 1, 8), '-',
                        SUBSTR(u.current_ett_uuid_hex, 9, 4), '-',
                        SUBSTR(u.current_ett_uuid_hex, 13, 4), '-',
                        SUBSTR(u.current_ett_uuid_hex, 17, 4), '-',
                        SUBSTR(u.current_ett_uuid_hex, 21, 12)
                    ))
                ) THEN 1
            WHEN u.item_code = '223900'
                AND u.observation_key = CONCAT(
                    'Observation/',
                    LOWER(CONCAT(
                        SUBSTR(u.prior_ett_uuid_hex, 1, 8), '-',
                        SUBSTR(u.prior_ett_uuid_hex, 9, 4), '-',
                        SUBSTR(u.prior_ett_uuid_hex, 13, 4), '-',
                        SUBSTR(u.prior_ett_uuid_hex, 17, 4), '-',
                        SUBSTR(u.prior_ett_uuid_hex, 21, 12)
                    ))
                ) THEN 1
            ELSE 0
        END AS is_ett
    FROM uuid_forms u
), pivoted AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        MAX(CASE
            WHEN item_code = '223901' THEN quantity_value
            ELSE NULL
        END) AS gcsmotor,
        MAX(CASE
            WHEN item_code = '223900' AND is_ett = 1 THEN CAST(0 AS DOUBLE)
            WHEN item_code = '223900' THEN quantity_value
            ELSE NULL
        END) AS gcsverbal,
        MAX(CASE
            WHEN item_code = '220739' THEN quantity_value
            ELSE NULL
        END) AS gcseyes,
        MAX(CASE
            WHEN item_code = '223900' AND is_ett = 1 THEN 1
            ELSE 0
        END) AS endotrachflag
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
