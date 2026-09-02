-- Readability copy -- not the artifact a server loads.
--
-- Library.icustay_hourly.json in this directory is authoritative. This SQL is
-- the decoded form of its content.data, byte-identical to the sql-text
-- extension beside it.
--
-- HAND-EDITED: this concept carries the Pathling SQL-allowlist rewrites
-- (TIMESTAMPDIFF/TIMESTAMPADD, LATERAL VIEW, HAVING). It is NOT what
-- `mimic-utils metrics-finalize` produces -- see PATHLING_WORKAROUNDS.md.

WITH all_hours AS (
    SELECT
        it.icu_encounter_key,
        it.patient_key,
        CASE
            WHEN DATE_TRUNC('HOUR', it.intime_hr) = it.intime_hr
                THEN CAST(it.intime_hr AS TIMESTAMP_NTZ)
            ELSE CAST(DATE_TRUNC('HOUR', it.intime_hr) + INTERVAL 1 HOUR AS TIMESTAMP_NTZ)
        END AS endtime,
        SEQUENCE(
            CAST(-24 AS BIGINT),
            CAST(
                CEIL(
                    CAST((UNIX_TIMESTAMP(DATE_TRUNC('HOUR', it.outtime_hr)) - UNIX_TIMESTAMP(DATE_TRUNC('HOUR', it.intime_hr))) / 3600 AS BIGINT)
                ) AS BIGINT
            )
        ) AS hrs,
        CAST(e.stay_id_str AS INTEGER) AS stay_id
    FROM icustay_times it
    INNER JOIN icustay_hourly_icu_encounter e
        ON it.icu_encounter_key = e.icu_encounter_key
    WHERE e.stay_id_str IS NOT NULL
)
, exploded AS (
    SELECT
        icu_encounter_key,
        patient_key,
        endtime,
        EXPLODE(hrs) AS hr_unnested
    FROM all_hours
)
SELECT
    CAST(hr_unnested AS BIGINT) AS hr,
    CAST((endtime + hr_unnested * INTERVAL 1 HOUR) AS TIMESTAMP_NTZ) AS endtime,
    icu_encounter_key,
    patient_key
FROM exploded
;
