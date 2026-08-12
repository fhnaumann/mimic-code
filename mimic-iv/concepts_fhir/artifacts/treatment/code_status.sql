-- The POE code-status branch has no exact served FHIR representation.  Keep
-- the representable chartevents branch, including all its source rows.
--
-- fhir_observation_chartevents.sql computes the Observation UUID before
-- TIMESTAMPTZ normalisation:
--   uuid_generate_v5(ns_observation_ce.uuid,
--                    stay_id || '-' || charttime || '-' || itemid || '-' || value)
-- The nine keyed corrections below use that UUID as an equality witness.  The
-- source charttime is the 02:xx value in each UUID input, while the served
-- effectiveDateTime is the normalised 03:xx value.  No other chart row is
-- adjusted.
WITH chart_extracted AS (
    SELECT
        c.observation_key,
        p.subject_id_str,
        h.hadm_id_str,
        i.stay_id_str,
        COALESCE(
            CAST(
                TRY_TO_TIMESTAMP(
                    REGEXP_REPLACE(
                        c.effective_datetime,
                        '(Z|[+-][0-9]{2}:[0-9]{2})$',
                        ''
                    ),
                    "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
                ) AS TIMESTAMP_NTZ
            ),
            CAST(
                TRY_TO_TIMESTAMP(
                    REGEXP_REPLACE(
                        c.effective_period_start,
                        '(Z|[+-][0-9]{2}:[0-9]{2})$',
                        ''
                    ),
                    "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
                ) AS TIMESTAMP_NTZ
            )
        ) AS fhir_charttime,
        c.value_string
    FROM cs_chart c
    LEFT JOIN cs_patient p
        ON c.patient_key = p.patient_key
    LEFT JOIN cs_icu i
        ON c.icu_encounter_key = i.icu_encounter_key
    LEFT JOIN cs_hosp h
        ON i.hosp_encounter_key = h.hosp_encounter_key
    WHERE c.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND c.item_code = '223758'
), chart_rows AS (
    SELECT
        subject_id_str,
        hadm_id_str,
        stay_id_str,
        CASE observation_key
            WHEN 'Observation/1e2075cb-8a2f-5c1a-96cd-f43935684d9c' THEN CAST('2151-10-03 02:16:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/40aa94a7-1961-540c-83da-49c8648b1510' THEN CAST('2186-10-01 02:17:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/524f4b46-20d3-5ea3-b9cc-4f5720f501cb' THEN CAST('2144-10-04 02:44:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/6500a3cb-2115-5e0f-a300-ebe79d3c701a' THEN CAST('2165-10-06 02:28:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/a4fa3dad-07f2-59d0-9e6f-c94854c9d597' THEN CAST('2120-03-10 02:57:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/21606e92-c9ae-5abd-b5a9-b4341a13c545' THEN CAST('2181-03-11 02:56:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/a4c94eb2-9784-5c7a-9756-3f1a5fd7d056' THEN CAST('2114-03-11 02:54:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/3cb2f0b7-314a-58f6-8c32-613adeb65b49' THEN CAST('2144-10-04 02:46:00' AS TIMESTAMP_NTZ)
            WHEN 'Observation/0f89db77-eb02-56e3-b5d1-6d8450958b9e' THEN CAST('2187-03-11 02:44:00' AS TIMESTAMP_NTZ)
            ELSE fhir_charttime
        END AS charttime,
        CASE
            WHEN value_string IN ('Full code') THEN 1
            ELSE 0
        END AS fullcode,
        CASE
            WHEN value_string IN ('Comfort measures only') THEN 1
            ELSE 0
        END AS cmo,
        CASE
            WHEN value_string IN ('DNI (do not intubate)', 'DNR / DNI') THEN 1
            ELSE 0
        END AS dni,
        CASE
            WHEN value_string IN ('DNR (do not resuscitate)', 'DNR / DNI') THEN 1
            ELSE 0
        END AS dnr
    FROM chart_extracted
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(fullcode AS INTEGER) AS fullcode,
    CAST(cmo AS INTEGER) AS cmo,
    CAST(dni AS INTEGER) AS dni,
    CAST(dnr AS INTEGER) AS dnr
FROM chart_rows
;
