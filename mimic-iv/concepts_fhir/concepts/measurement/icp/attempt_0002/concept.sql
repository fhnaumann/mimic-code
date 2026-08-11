-- Chartevents Observation.id is generated from the pre-TIMESTAMPTZ source
-- charttime and source value, while effectiveDateTime contains the possibly
-- normalized served time. Recompute that UUIDv5 relation for the served time
-- and for exactly one hour earlier; only an ID that proves the earlier input
-- restores the source wall time, so genuine 03:xx observations are unchanged.
WITH observation_rows AS (
    SELECT
        o.observation_key,
        o.patient_key,
        o.encounter_key,
        o.item_code,
        o.code_system,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS fhir_charttime,
        o.quantity_value,
        o.value_string,
        CAST(o.quantity_value AS DOUBLE) AS quantity_num,
        CASE
            WHEN o.value_string IS NOT NULL THEN o.value_string
            WHEN o.quantity_value LIKE '%.%' THEN
                REGEXP_REPLACE(
                    REGEXP_REPLACE(o.quantity_value, '0+$', ''),
                    '[.]$',
                    ''
                )
            ELSE o.quantity_value
        END AS uuid_value
    FROM icp_observation o
    WHERE o.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('220765', '227989')
), identified_rows AS (
    SELECT
        o.*,
        p.subject_id_str,
        e.stay_id_str
    FROM observation_rows o
    INNER JOIN icp_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN icp_icu_encounter e
        ON o.encounter_key = e.encounter_key
        AND o.patient_key = e.patient_key
    WHERE p.subject_id_str IS NOT NULL
        AND e.stay_id_str IS NOT NULL
), uuid_names AS (
    SELECT
        i.*,
        CONCAT(
            i.stay_id_str, '-', CAST(i.fhir_charttime AS STRING),
            '-', i.item_code, '-', i.uuid_value
        ) AS current_name,
        CONCAT(
            i.stay_id_str, '-',
            CAST(i.fhir_charttime - INTERVAL 1 HOUR AS STRING),
            '-', i.item_code, '-', i.uuid_value
        ) AS earlier_name
    FROM identified_rows i
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
), grouped AS (
    SELECT
        subject_id_str,
        stay_id_str,
        charttime,
        MAX(
            CASE
                WHEN quantity_num > 0 AND quantity_num < 100 THEN quantity_num
                ELSE NULL
            END
        ) AS icp
    FROM recovered_rows
    GROUP BY subject_id_str, stay_id_str, charttime
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(icp AS FLOAT) AS icp
FROM grouped
;
