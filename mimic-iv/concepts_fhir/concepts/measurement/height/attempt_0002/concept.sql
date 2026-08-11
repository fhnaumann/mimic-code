-- Chartevents Observation.id is built from the pre-TIMESTAMPTZ charttime,
-- while Observation.effectiveDateTime contains the normalized value.  The
-- UUIDv5 witness lets the source wall time be recovered without shifting
-- genuine 03:xx observations.
WITH observation_rows AS (
    SELECT
        o.observation_key,
        o.encounter_key,
        o.patient_key,
        o.item_code,
        o.item_system,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS effective_datetime_ntz,
        TRY_CAST(o.effective_period_start AS TIMESTAMP_NTZ) AS effective_period_start_ntz,
        o.quantity_value,
        CAST(o.quantity_value AS DOUBLE) AS quantity_num
    FROM height_observation o
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('226707', '226730')
        AND o.quantity_value IS NOT NULL
), identified_rows AS (
    SELECT
        o.*,
        p.subject_id_str,
        e.stay_id_str
    FROM observation_rows o
    INNER JOIN height_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN height_encounter e
        ON o.encounter_key = e.encounter_key
    WHERE p.subject_id_str IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), typed_rows AS (
    SELECT
        i.*,
        COALESCE(i.effective_datetime_ntz, i.effective_period_start_ntz) AS fhir_charttime
    FROM identified_rows i
), uuid_names AS (
    SELECT
        t.*,
        CONCAT(
            t.stay_id_str, '-', CAST(t.fhir_charttime AS STRING),
            '-', t.item_code, '-', t.quantity_value
        ) AS current_name,
        CONCAT(
            t.stay_id_str, '-', CAST(t.fhir_charttime - INTERVAL 1 HOUR AS STRING),
            '-', t.item_code, '-', t.quantity_value
        ) AS earlier_name
    FROM typed_rows t
), uuid_digests AS (
    SELECT
        n.*,
        SHA1(
            CONCAT(
                UNHEX('36e18860b4aa5577bc80a5b07922cd3d'),
                ENCODE(n.current_name, 'UTF-8')
            )
        ) AS current_digest,
        SHA1(
            CONCAT(
                UNHEX('36e18860b4aa5577bc80a5b07922cd3d'),
                ENCODE(n.earlier_name, 'UTF-8')
            )
        ) AS earlier_digest
    FROM uuid_names n
), uuid_forms AS (
    SELECT
        d.*,
        CONCAT(
            SUBSTR(d.current_digest, 1, 12),
            '5',
            SUBSTR(d.current_digest, 14, 3),
            CASE LOWER(SUBSTR(d.current_digest, 17, 1))
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
            SUBSTR(d.current_digest, 18)
        ) AS current_uuid_hex,
        CONCAT(
            SUBSTR(d.earlier_digest, 1, 12),
            '5',
            SUBSTR(d.earlier_digest, 14, 3),
            CASE LOWER(SUBSTR(d.earlier_digest, 17, 1))
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
            SUBSTR(d.earlier_digest, 18)
        ) AS earlier_uuid_hex
    FROM uuid_digests d
), recovered_rows AS (
    SELECT
        u.subject_id_str,
        u.stay_id_str,
        u.item_code,
        u.quantity_num,
        CASE
            WHEN u.observation_key = CONCAT(
                'Observation/',
                LOWER(CONCAT(
                    SUBSTR(u.current_uuid_hex, 1, 8), '-',
                    SUBSTR(u.current_uuid_hex, 9, 4), '-',
                    SUBSTR(u.current_uuid_hex, 13, 4), '-',
                    SUBSTR(u.current_uuid_hex, 17, 4), '-',
                    SUBSTR(u.current_uuid_hex, 21, 12)
                ))
            ) THEN u.fhir_charttime
            WHEN u.observation_key = CONCAT(
                'Observation/',
                LOWER(CONCAT(
                    SUBSTR(u.earlier_uuid_hex, 1, 8), '-',
                    SUBSTR(u.earlier_uuid_hex, 9, 4), '-',
                    SUBSTR(u.earlier_uuid_hex, 13, 4), '-',
                    SUBSTR(u.earlier_uuid_hex, 17, 4), '-',
                    SUBSTR(u.earlier_uuid_hex, 21, 12)
                ))
            ) THEN u.fhir_charttime - INTERVAL 1 HOUR
            ELSE u.fhir_charttime
        END AS charttime
    FROM uuid_forms u
), ht_in AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        ROUND(quantity_num * 2.54, 2) AS height
    FROM recovered_rows
    WHERE item_code = '226707'
), ht_cm AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        ROUND(quantity_num, 2) AS height
    FROM recovered_rows
    WHERE item_code = '226730'
), ht_stg0 AS (
    SELECT
        COALESCE(h1.subject_id_str, h2.subject_id_str) AS subject_id_str,
        COALESCE(h1.stay_id_str, h2.stay_id_str) AS stay_id_str,
        COALESCE(h1.charttime, h2.charttime) AS charttime,
        COALESCE(h1.height, h2.height) AS height
    FROM ht_cm h1
    FULL OUTER JOIN ht_in h2
        ON h1.subject_id_str = h2.subject_id_str
        AND h1.charttime = h2.charttime
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(height AS DECIMAL(38,2)) AS height
FROM ht_stg0
WHERE height IS NOT NULL
    AND height > 120
    AND height < 230
;
