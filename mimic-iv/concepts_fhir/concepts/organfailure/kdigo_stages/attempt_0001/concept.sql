WITH icu_stays AS (
    SELECT
        e.icu_encounter_key,
        e.patient_key,
        e.parent_encounter_key,
        e.stay_id_str,
        TRY_CAST(e.intime_datetime AS TIMESTAMP_NTZ) AS intime
    FROM kdigo_stages_icu_encounter AS e
    WHERE e.stay_id_str IS NOT NULL
), hospital_encounters AS (
    SELECT
        h.encounter_key,
        h.hadm_id_str
    FROM kdigo_stages_hospital_encounter AS h
    WHERE h.hadm_id_str IS NOT NULL
), patient_ids AS (
    SELECT
        p.patient_key,
        p.subject_id_str
    FROM kdigo_stages_patient AS p
    WHERE p.subject_id_str IS NOT NULL
), icu_spine AS (
    SELECT
        i.icu_encounter_key,
        i.patient_key,
        i.stay_id_str,
        i.intime,
        h.encounter_key,
        h.hadm_id_str,
        p.subject_id_str
    FROM icu_stays AS i
    LEFT JOIN hospital_encounters AS h
        ON i.parent_encounter_key = h.encounter_key
    LEFT JOIN patient_ids AS p
        ON i.patient_key = p.patient_key
), cr_stg AS (
    SELECT
        cr.icu_encounter_key,
        cr.charttime,
        cr.creat_low_past_7day,
        cr.creat_low_past_48hr,
        cr.creat,
        CASE
            WHEN cr.creat >= (cr.creat_low_past_7day * 3.0) THEN 3
            WHEN cr.creat >= 4
                AND (
                    cr.creat >= (cr.creat_low_past_48hr + 0.3)
                    OR cr.creat >= (1.5 * cr.creat_low_past_7day)
                )
                THEN 3
            WHEN cr.creat >= (cr.creat_low_past_7day * 2.0) THEN 2
            WHEN cr.creat >= (cr.creat_low_past_48hr + 0.3) THEN 1
            WHEN cr.creat >= (cr.creat_low_past_7day * 1.5) THEN 1
            ELSE 0
        END AS aki_stage_creat
    FROM kdigo_creatinine AS cr
), uo_stg AS (
    SELECT
        uo.icu_encounter_key,
        uo.charttime,
        uo.weight,
        uo.uo_rt_6hr,
        uo.uo_rt_12hr,
        uo.uo_rt_24hr,
        CASE
            WHEN uo.uo_rt_6hr IS NULL THEN NULL
            WHEN uo.charttime <= ie.intime + INTERVAL 6 HOURS THEN 0
            WHEN uo.uo_tm_24hr >= 24 AND uo.uo_rt_24hr < 0.3 THEN 3
            WHEN uo.uo_tm_12hr >= 12 AND uo.uo_rt_12hr = 0 THEN 3
            WHEN uo.uo_tm_12hr >= 12 AND uo.uo_rt_12hr < 0.5 THEN 2
            WHEN uo.uo_tm_6hr >= 6 AND uo.uo_rt_6hr < 0.5 THEN 1
            ELSE 0
        END AS aki_stage_uo
    FROM kdigo_uo AS uo
    INNER JOIN icu_stays AS ie
        ON uo.icu_encounter_key = ie.icu_encounter_key
), crrt_stg AS (
    SELECT
        c.icu_encounter_key,
        c.charttime,
        CASE
            WHEN c.charttime IS NOT NULL THEN 3
            ELSE NULL
        END AS aki_stage_crrt
    FROM crrt AS c
    WHERE c.crrt_mode IS NOT NULL
), tm_stg AS (
    SELECT
        icu_encounter_key,
        charttime
    FROM cr_stg
    UNION DISTINCT
    SELECT
        icu_encounter_key,
        charttime
    FROM uo_stg
    UNION DISTINCT
    SELECT
        icu_encounter_key,
        charttime
    FROM crrt_stg
)
SELECT
    CAST(ie.subject_id_str AS INTEGER) AS subject_id,
    CAST(ie.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(ie.stay_id_str AS INTEGER) AS stay_id,
    CAST(tm.charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(cr.creat_low_past_7day AS DOUBLE) AS creat_low_past_7day,
    CAST(cr.creat_low_past_48hr AS DOUBLE) AS creat_low_past_48hr,
    CAST(cr.creat AS DOUBLE) AS creat,
    CAST(cr.aki_stage_creat AS INTEGER) AS aki_stage_creat,
    CAST(uo.uo_rt_6hr AS DECIMAL(38,4)) AS uo_rt_6hr,
    CAST(uo.uo_rt_12hr AS DECIMAL(38,4)) AS uo_rt_12hr,
    CAST(uo.uo_rt_24hr AS DECIMAL(38,4)) AS uo_rt_24hr,
    CAST(uo.aki_stage_uo AS INTEGER) AS aki_stage_uo,
    CAST(crrt.aki_stage_crrt AS INTEGER) AS aki_stage_crrt,
    CAST(
        GREATEST(
            COALESCE(cr.aki_stage_creat, 0),
            COALESCE(uo.aki_stage_uo, 0),
            COALESCE(crrt.aki_stage_crrt, 0)
        ) AS INTEGER
    ) AS aki_stage,
    CAST(
        MAX(
            GREATEST(
                COALESCE(cr.aki_stage_creat, 0),
                COALESCE(uo.aki_stage_uo, 0),
                COALESCE(crrt.aki_stage_crrt, 0)
            )
        ) OVER (
            PARTITION BY ie.patient_key
            ORDER BY TIMESTAMPDIFF(SECOND, ie.intime, tm.charttime)
            RANGE BETWEEN 21600 PRECEDING AND CURRENT ROW
        ) AS INTEGER
    ) AS aki_stage_smoothed,
    ie.patient_key AS patient_key,
    ie.encounter_key AS encounter_key,
    ie.icu_encounter_key AS icu_encounter_key
FROM icu_spine AS ie
LEFT JOIN tm_stg AS tm
    ON ie.icu_encounter_key = tm.icu_encounter_key
LEFT JOIN cr_stg AS cr
    ON ie.icu_encounter_key = cr.icu_encounter_key
    AND tm.charttime = cr.charttime
LEFT JOIN uo_stg AS uo
    ON ie.icu_encounter_key = uo.icu_encounter_key
    AND tm.charttime = uo.charttime
LEFT JOIN crrt_stg AS crrt
    ON ie.icu_encounter_key = crrt.icu_encounter_key
    AND tm.charttime = crrt.charttime
;
