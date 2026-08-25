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
                    TIMESTAMPDIFF(
                        HOUR,
                        DATE_TRUNC('HOUR', it.intime_hr),
                        DATE_TRUNC('HOUR', it.outtime_hr)
                    )
                ) AS BIGINT
            )
        ) AS hrs,
        CAST(e.stay_id_str AS INTEGER) AS stay_id
    FROM icustay_times it
    INNER JOIN icustay_hourly_icu_encounter e
        ON it.icu_encounter_key = e.icu_encounter_key
    WHERE e.stay_id_str IS NOT NULL
)
SELECT
    CAST(stay_id AS INTEGER) AS stay_id,
    CAST(hr_unnested AS BIGINT) AS hr,
    CAST(TIMESTAMPADD(HOUR, hr_unnested, endtime) AS TIMESTAMP_NTZ) AS endtime,
    icu_encounter_key,
    patient_key
FROM all_hours
LATERAL VIEW EXPLODE(hrs) exploded AS hr_unnested
;
