-- The chartevents ETL computes Observation.id from the pre-TIMESTAMPTZ
-- charttime (mimic-fhir/sql/fhir_observation_chartevents.sql:21), then writes
-- the DST-normalized time at line 67.  Recompute that UUIDv5 relation for the
-- served time and for exactly one hour earlier.  Only an ID that proves the
-- earlier input is restored; genuine 03:xx observations keep their time.
WITH observation_rows AS (
    SELECT
        o.observation_key,
        o.encounter_key,
        o.item_code,
        o.code_system,
        o.effective_datetime,
        o.effective_period_start,
        o.quantity_value,
        o.string_value
    FROM crrt_observation o
    WHERE o.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN (
            '227290', '224146', '224149', '224144', '228004', '225183',
            '225977', '224154', '224151', '224150', '225958', '224145',
            '224191', '228005', '228006', '225976', '224153', '224152',
            '226457'
        )
        AND (o.quantity_value IS NOT NULL OR o.string_value IS NOT NULL)
), typed_rows AS (
    SELECT
        o.observation_key,
        e.stay_id_str,
        COALESCE(
            CAST(
                TRY_TO_TIMESTAMP(
                    REGEXP_REPLACE(
                        o.effective_datetime,
                        '(Z|[+-][0-9]{2}:[0-9]{2})$',
                        ''
                    ),
                    "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
                ) AS TIMESTAMP_NTZ
            ),
            CAST(
                TRY_TO_TIMESTAMP(
                    REGEXP_REPLACE(
                        o.effective_period_start,
                        '(Z|[+-][0-9]{2}:[0-9]{2})$',
                        ''
                    ),
                    "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
                ) AS TIMESTAMP_NTZ
            )
        ) AS fhir_charttime,
        o.item_code,
        CAST(o.quantity_value AS DOUBLE) AS quantity_value,
        o.string_value,
        COALESCE(
            o.string_value,
            CASE
                WHEN o.quantity_value LIKE '%.%' THEN
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(o.quantity_value, '0+$', ''),
                        '[.]$',
                        ''
                    )
                ELSE o.quantity_value
            END
        ) AS uuid_value
    FROM observation_rows o
    INNER JOIN crrt_encounter e
        ON o.encounter_key = e.encounter_key
), uuid_names AS (
    SELECT
        t.*,
        CONCAT(
            t.stay_id_str, '-',
            CAST(t.fhir_charttime AS STRING), '-',
            t.item_code, '-',
            t.uuid_value
        ) AS current_name,
        CONCAT(
            t.stay_id_str, '-',
            CAST(t.fhir_charttime - INTERVAL 1 HOUR AS STRING), '-',
            t.item_code, '-',
            t.uuid_value
        ) AS recovered_name
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
                ENCODE(n.recovered_name, 'UTF-8')
            )
        ) AS recovered_digest
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
            SUBSTR(d.recovered_digest, 1, 12),
            '5',
            SUBSTR(d.recovered_digest, 14, 3),
            CASE LOWER(SUBSTR(d.recovered_digest, 17, 1))
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
            SUBSTR(d.recovered_digest, 18)
        ) AS recovered_uuid_hex
    FROM uuid_digests d
), recovered_rows AS (
    SELECT
        u.stay_id_str,
        CASE
            WHEN u.observation_key = CONCAT(
                'Observation/',
                LOWER(CONCAT(
                    SUBSTR(u.recovered_uuid_hex, 1, 8), '-',
                    SUBSTR(u.recovered_uuid_hex, 9, 4), '-',
                    SUBSTR(u.recovered_uuid_hex, 13, 4), '-',
                    SUBSTR(u.recovered_uuid_hex, 17, 4), '-',
                    SUBSTR(u.recovered_uuid_hex, 21, 12)
                ))
            )
            AND u.observation_key <> CONCAT(
                'Observation/',
                LOWER(CONCAT(
                    SUBSTR(u.current_uuid_hex, 1, 8), '-',
                    SUBSTR(u.current_uuid_hex, 9, 4), '-',
                    SUBSTR(u.current_uuid_hex, 13, 4), '-',
                    SUBSTR(u.current_uuid_hex, 17, 4), '-',
                    SUBSTR(u.current_uuid_hex, 21, 12)
                ))
            )
            THEN u.fhir_charttime - INTERVAL 1 HOUR
            ELSE u.fhir_charttime
        END AS charttime,
        u.item_code,
        u.quantity_value,
        u.string_value
    FROM uuid_forms u
), pivoted AS (
    SELECT
        stay_id_str,
        charttime,
        MAX(CASE WHEN item_code = '227290' THEN string_value END) AS crrt_mode,
        MAX(CASE WHEN item_code = '224149' THEN quantity_value END) AS access_pressure,
        MAX(CASE WHEN item_code = '224144' THEN quantity_value END) AS blood_flow,
        MAX(CASE WHEN item_code = '228004' THEN quantity_value END) AS citrate,
        MAX(CASE WHEN item_code = '225183' THEN quantity_value END) AS current_goal,
        MAX(CASE WHEN item_code = '225977' THEN string_value END) AS dialysate_fluid,
        MAX(CASE WHEN item_code = '224154' THEN quantity_value END) AS dialysate_rate,
        MAX(CASE WHEN item_code = '224151' THEN quantity_value END) AS effluent_pressure,
        MAX(CASE WHEN item_code = '224150' THEN quantity_value END) AS filter_pressure,
        MAX(CASE WHEN item_code = '225958' THEN string_value END) AS heparin_concentration,
        MAX(CASE WHEN item_code = '224145' THEN quantity_value END) AS heparin_dose,
        MAX(CASE WHEN item_code = '224191' THEN quantity_value END) AS hourly_patient_fluid_removal,
        MAX(CASE WHEN item_code = '228005' THEN quantity_value END) AS prefilter_replacement_rate,
        MAX(CASE WHEN item_code = '228006' THEN quantity_value END) AS postfilter_replacement_rate,
        MAX(CASE WHEN item_code = '225976' THEN string_value END) AS replacement_fluid,
        MAX(CASE WHEN item_code = '224153' THEN quantity_value END) AS replacement_rate,
        MAX(CASE WHEN item_code = '224152' THEN quantity_value END) AS return_pressure,
        MAX(CASE WHEN item_code = '226457' THEN quantity_value END) AS ultrafiltrate_output,
        MAX(
            CASE
                WHEN item_code = '224146'
                    AND string_value IN ('Active', 'Initiated', 'Reinitiated', 'New Filter')
                    THEN 1
                WHEN item_code = '224146'
                    AND string_value IN ('Recirculating', 'Discontinued')
                    THEN 0
                ELSE NULL
            END
        ) AS system_active,
        MAX(
            CASE
                WHEN item_code = '224146' AND string_value IN ('Clots Present') THEN 1
                WHEN item_code = '224146' AND string_value IN ('No Clot Present') THEN 0
                ELSE NULL
            END
        ) AS clots,
        MAX(
            CASE
                WHEN item_code = '224146'
                    AND string_value IN ('Clots Increasing', 'Clot Increasing')
                    THEN 1
                ELSE NULL
            END
        ) AS clots_increasing,
        MAX(
            CASE
                WHEN item_code = '224146' AND string_value IN ('Clotted') THEN 1
                ELSE NULL
            END
        ) AS clotted
    FROM recovered_rows
    GROUP BY stay_id_str, charttime
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(crrt_mode AS VARCHAR(255)) AS crrt_mode,
    CAST(access_pressure AS FLOAT) AS access_pressure,
    CAST(blood_flow AS FLOAT) AS blood_flow,
    CAST(citrate AS FLOAT) AS citrate,
    CAST(current_goal AS FLOAT) AS current_goal,
    CAST(dialysate_fluid AS VARCHAR(255)) AS dialysate_fluid,
    CAST(dialysate_rate AS FLOAT) AS dialysate_rate,
    CAST(effluent_pressure AS FLOAT) AS effluent_pressure,
    CAST(filter_pressure AS FLOAT) AS filter_pressure,
    CAST(heparin_concentration AS VARCHAR(255)) AS heparin_concentration,
    CAST(heparin_dose AS FLOAT) AS heparin_dose,
    CAST(hourly_patient_fluid_removal AS FLOAT) AS hourly_patient_fluid_removal,
    CAST(prefilter_replacement_rate AS FLOAT) AS prefilter_replacement_rate,
    CAST(postfilter_replacement_rate AS FLOAT) AS postfilter_replacement_rate,
    CAST(replacement_fluid AS VARCHAR(255)) AS replacement_fluid,
    CAST(replacement_rate AS FLOAT) AS replacement_rate,
    CAST(return_pressure AS FLOAT) AS return_pressure,
    CAST(ultrafiltrate_output AS FLOAT) AS ultrafiltrate_output,
    CAST(system_active AS INTEGER) AS system_active,
    CAST(clots AS INTEGER) AS clots,
    CAST(clots_increasing AS INTEGER) AS clots_increasing,
    CAST(clotted AS INTEGER) AS clotted
FROM pivoted
;
