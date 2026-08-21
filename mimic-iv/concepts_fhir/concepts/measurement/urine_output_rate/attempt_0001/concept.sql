WITH icu_encounters AS (
    SELECT
        e.icu_encounter_key,
        e.patient_key,
        e.stay_id_str,
        TRY_CAST(e.intime_datetime AS TIMESTAMP_NTZ) AS intime,
        TRY_CAST(e.outtime_datetime AS TIMESTAMP_NTZ) AS outtime
    FROM urine_output_rate_icu_encounter e
    WHERE e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
        AND e.stay_id_str IS NOT NULL
), heart_rate_observations AS (
    SELECT
        o.encounter_key,
        COALESCE(
            TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ),
            TRY_CAST(o.effective_period_start AS TIMESTAMP_NTZ),
            TRY_CAST(o.effective_instant AS TIMESTAMP_NTZ)
        ) AS charttime,
        o.item_code,
        o.item_system
    FROM urine_output_rate_observation o
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code = '220045'
), tm AS (
    SELECT
        e.icu_encounter_key,
        e.patient_key,
        e.stay_id_str,
        MIN(c.charttime) AS intime_hr,
        MAX(c.charttime) AS outtime_hr
    FROM icu_encounters e
    INNER JOIN heart_rate_observations c
        ON e.icu_encounter_key = c.encounter_key
        AND c.charttime > e.intime - INTERVAL 1 MONTH
        AND c.charttime < e.outtime + INTERVAL 1 MONTH
    GROUP BY
        e.icu_encounter_key,
        e.patient_key,
        e.stay_id_str
), uo_ordered AS (
    SELECT
        tm.icu_encounter_key,
        tm.patient_key,
        tm.stay_id_str,
        tm.intime_hr,
        u.charttime,
        u.urineoutput,
        LAG(u.charttime) OVER (
            PARTITION BY tm.icu_encounter_key
            ORDER BY u.charttime
        ) AS previous_charttime
    FROM tm
    INNER JOIN urine_output u
        ON tm.icu_encounter_key = u.icu_encounter_key
), uo_tm AS (
    SELECT
        icu_encounter_key,
        patient_key,
        stay_id_str,
        CASE
            WHEN previous_charttime IS NULL
                THEN TIMESTAMPDIFF(MINUTE, intime_hr, charttime)
            ELSE TIMESTAMPDIFF(MINUTE, previous_charttime, charttime)
        END AS tm_since_last_uo,
        charttime,
        urineoutput
    FROM uo_ordered
), ur_stg AS (
    SELECT
        io.icu_encounter_key,
        io.patient_key,
        io.stay_id_str,
        io.charttime,
        SUM(DISTINCT io.urineoutput) AS uo,
        SUM(
            CASE
                WHEN TIMESTAMPDIFF(HOUR, iosum.charttime, io.charttime) <= 5
                    THEN iosum.urineoutput
                ELSE NULL
            END
        ) AS urineoutput_6hr,
        ROUND(
            CAST(
                SUM(
                    CASE
                        WHEN TIMESTAMPDIFF(HOUR, iosum.charttime, io.charttime) <= 5
                            THEN iosum.tm_since_last_uo
                        ELSE NULL
                    END
                ) / 60.0 AS DECIMAL(38,12)
            ),
            6
        ) AS uo_tm_6hr,
        SUM(
            CASE
                WHEN TIMESTAMPDIFF(HOUR, iosum.charttime, io.charttime) <= 11
                    THEN iosum.urineoutput
                ELSE NULL
            END
        ) AS urineoutput_12hr,
        ROUND(
            CAST(
                SUM(
                    CASE
                        WHEN TIMESTAMPDIFF(HOUR, iosum.charttime, io.charttime) <= 11
                            THEN iosum.tm_since_last_uo
                        ELSE NULL
                    END
                ) / 60.0 AS DECIMAL(38,12)
            ),
            6
        ) AS uo_tm_12hr,
        SUM(iosum.urineoutput) AS urineoutput_24hr,
        ROUND(
            CAST(SUM(iosum.tm_since_last_uo) / 60.0 AS DECIMAL(38,12)),
            6
        ) AS uo_tm_24hr
    FROM uo_tm io
    LEFT JOIN uo_tm iosum
        ON io.icu_encounter_key = iosum.icu_encounter_key
        AND io.charttime >= iosum.charttime
        AND io.charttime <= iosum.charttime + INTERVAL 23 HOURS
    GROUP BY
        io.icu_encounter_key,
        io.patient_key,
        io.stay_id_str,
        io.charttime
), weighted_rows AS (
    SELECT
        ur.icu_encounter_key,
        ur.patient_key,
        ur.stay_id_str,
        ur.charttime,
        wd.weight,
        ur.uo,
        ur.urineoutput_6hr,
        ur.urineoutput_12hr,
        ur.urineoutput_24hr,
        ur.uo_tm_6hr,
        ur.uo_tm_12hr,
        ur.uo_tm_24hr
    FROM ur_stg ur
    LEFT JOIN weight_durations wd
        ON ur.icu_encounter_key = wd.icu_encounter_key
        AND ur.charttime > wd.starttime
        AND ur.charttime <= wd.endtime
        AND wd.weight > 0
)
SELECT
    CAST(w.stay_id_str AS INTEGER) AS stay_id,
    CAST(w.charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(w.weight AS DECIMAL(38,3)) AS weight,
    CAST(w.uo AS DOUBLE) AS uo,
    CAST(w.urineoutput_6hr AS DOUBLE) AS urineoutput_6hr,
    CAST(w.urineoutput_12hr AS DOUBLE) AS urineoutput_12hr,
    CAST(w.urineoutput_24hr AS DOUBLE) AS urineoutput_24hr,
    CAST(
        CASE
            WHEN w.uo_tm_6hr >= 6 THEN ROUND(
                CAST(
                    w.urineoutput_6hr / w.weight / w.uo_tm_6hr
                    AS DECIMAL(38,12)
                ),
                4
            )
            ELSE NULL
        END AS DECIMAL(38,4)
    ) AS uo_mlkghr_6hr,
    CAST(
        CASE
            WHEN w.uo_tm_12hr >= 12 THEN ROUND(
                CAST(
                    w.urineoutput_12hr / w.weight / w.uo_tm_12hr
                    AS DECIMAL(38,12)
                ),
                4
            )
            ELSE NULL
        END AS DECIMAL(38,4)
    ) AS uo_mlkghr_12hr,
    CAST(
        CASE
            WHEN w.uo_tm_24hr >= 24 THEN ROUND(
                CAST(
                    w.urineoutput_24hr / w.weight / w.uo_tm_24hr
                    AS DECIMAL(38,12)
                ),
                4
            )
            ELSE NULL
        END AS DECIMAL(38,4)
    ) AS uo_mlkghr_24hr,
    CAST(ROUND(CAST(w.uo_tm_6hr AS DECIMAL(38,12)), 2) AS DECIMAL(38,2)) AS uo_tm_6hr,
    CAST(ROUND(CAST(w.uo_tm_12hr AS DECIMAL(38,12)), 2) AS DECIMAL(38,2)) AS uo_tm_12hr,
    CAST(ROUND(CAST(w.uo_tm_24hr AS DECIMAL(38,12)), 2) AS DECIMAL(38,2)) AS uo_tm_24hr,
    w.icu_encounter_key AS icu_encounter_key,
    w.patient_key AS patient_key
FROM weighted_rows w
;
