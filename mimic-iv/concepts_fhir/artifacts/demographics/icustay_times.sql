-- Observation.effectiveDateTime is normally the source wall-clock charttime.
-- The chartevents ETL builds Observation.id from the pre-TIMESTAMPTZ charttime,
-- so test that UUID witness at the served time and exactly one hour earlier.
-- Only an exact earlier UUID match recovers the source 02:xx value; genuine
-- 03:xx observations retain their served time.
WITH icu_encounters AS (
    SELECT
        encounter_key,
        patient_key,
        parent_encounter_key,
        stay_id_str
    FROM icustay_times_icu_encounter
    WHERE stay_id_str IS NOT NULL
), hospital_encounters AS (
    SELECT
        encounter_key,
        hadm_id_str
    FROM icustay_times_hospital_encounter
    WHERE hadm_id_str IS NOT NULL
), patient_ids AS (
    SELECT
        patient_key,
        subject_id_str
    FROM icustay_times_patient
    WHERE subject_id_str IS NOT NULL
), observation_rows AS (
    SELECT
        observation_key,
        encounter_key,
        item_code,
        item_system,
        COALESCE(
            TRY_CAST(effective_datetime AS TIMESTAMP_NTZ),
            TRY_CAST(effective_period_start AS TIMESTAMP_NTZ),
            TRY_CAST(effective_instant AS TIMESTAMP_NTZ)
        ) AS fhir_charttime,
        COALESCE(value_string, quantity_value) AS uuid_value
    FROM icustay_times_observation
    WHERE item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
      AND item_code = '220045'
), identified_observations AS (
    SELECT
        o.observation_key,
        o.item_code,
        o.fhir_charttime,
        o.uuid_value,
        i.stay_id_str
    FROM observation_rows o
    LEFT JOIN icu_encounters i
        ON o.encounter_key = i.encounter_key
    WHERE i.stay_id_str IS NOT NULL
), uuid_names AS (
    SELECT
        o.*,
        CONCAT(
            o.stay_id_str, '-', CAST(o.fhir_charttime AS STRING),
            '-', o.item_code, '-', o.uuid_value
        ) AS current_name,
        CONCAT(
            o.stay_id_str, '-',
            CAST(o.fhir_charttime - INTERVAL 1 HOUR AS STRING),
            '-', o.item_code, '-', o.uuid_value
        ) AS earlier_name
    FROM identified_observations o
), uuid_digests AS (
    SELECT
        n.*,
        LOWER(SHA1(
            CONCAT(
                UNHEX('36e18860b4aa5577bc80a5b07922cd3d'),
                ENCODE(n.current_name, 'UTF-8')
            )
        )) AS current_digest,
        LOWER(SHA1(
            CONCAT(
                UNHEX('36e18860b4aa5577bc80a5b07922cd3d'),
                ENCODE(n.earlier_name, 'UTF-8')
            )
        )) AS earlier_digest
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
), recovered_observations AS (
    SELECT
        u.stay_id_str,
        CASE
            WHEN LOWER(u.observation_key) = CONCAT(
                'observation/',
                LOWER(CONCAT(
                    SUBSTR(u.current_uuid_hex, 1, 8), '-',
                    SUBSTR(u.current_uuid_hex, 9, 4), '-',
                    SUBSTR(u.current_uuid_hex, 13, 4), '-',
                    SUBSTR(u.current_uuid_hex, 17, 4), '-',
                    SUBSTR(u.current_uuid_hex, 21, 12)
                ))
            ) THEN u.fhir_charttime
            WHEN LOWER(u.observation_key) = CONCAT(
                'observation/',
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
), heart_rate_times AS (
    SELECT
        stay_id_str,
        MIN(charttime) AS intime_hr,
        MAX(charttime) AS outtime_hr
    FROM recovered_observations
    WHERE charttime IS NOT NULL
    GROUP BY stay_id_str
)
SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(h.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(i.stay_id_str AS INTEGER) AS stay_id,
    CAST(hr.intime_hr AS TIMESTAMP_NTZ) AS intime_hr,
    CAST(hr.outtime_hr AS TIMESTAMP_NTZ) AS outtime_hr
FROM icu_encounters i
LEFT JOIN hospital_encounters h
    ON i.parent_encounter_key = h.encounter_key
LEFT JOIN patient_ids p
    ON i.patient_key = p.patient_key
LEFT JOIN heart_rate_times hr
    ON i.stay_id_str = hr.stay_id_str
;
