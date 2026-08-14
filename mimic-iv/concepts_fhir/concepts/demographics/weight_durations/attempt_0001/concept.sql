WITH observation_typed AS (
    SELECT
        o.encounter_key,
        o.item_code,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS effective_datetime_ntz,
        TRY_CAST(o.effective_period_start AS TIMESTAMP_NTZ) AS effective_period_start_ntz,
        TRY_CAST(o.effective_instant AS TIMESTAMP_NTZ) AS effective_instant_ntz,
        CAST(o.quantity_value AS DOUBLE) AS valuenum
    FROM weight_durations_observation o
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('226512', '224639')
), icu_stays AS (
    SELECT
        e.encounter_key,
        e.stay_id_str,
        TRY_CAST(e.intime_datetime AS TIMESTAMP_NTZ) AS intime,
        TRY_CAST(e.outtime_datetime AS TIMESTAMP_NTZ) AS outtime
    FROM weight_durations_icu_encounter e
    WHERE e.stay_id_str IS NOT NULL
), wt_stg AS (
    SELECT
        i.stay_id_str,
        COALESCE(
            o.effective_datetime_ntz,
            o.effective_period_start_ntz,
            o.effective_instant_ntz
        ) AS charttime,
        CASE WHEN o.item_code = '226512' THEN 'admit'
            ELSE 'daily' END AS weight_type,
        ROUND(o.valuenum, 3) AS weight
    FROM observation_typed o
    INNER JOIN icu_stays i
        ON i.encounter_key = o.encounter_key
    WHERE o.valuenum IS NOT NULL
        AND o.valuenum > 0
        AND o.valuenum < 1500
), wt_stg1 AS (
    SELECT
        stay_id_str,
        charttime,
        weight_type,
        weight,
        ROW_NUMBER() OVER (
            PARTITION BY stay_id_str, weight_type ORDER BY charttime
        ) AS rn
    FROM wt_stg
    WHERE weight IS NOT NULL
), wt_stg2 AS (
    SELECT
        w.stay_id_str,
        i.intime,
        i.outtime,
        w.weight_type,
        CASE WHEN w.weight_type = 'admit' AND w.rn = 1
            THEN i.intime - INTERVAL 2 HOURS
            ELSE w.charttime END AS starttime,
        w.weight
    FROM wt_stg1 w
    INNER JOIN icu_stays i
        ON i.stay_id_str = w.stay_id_str
), wt_stg3 AS (
    SELECT
        stay_id_str,
        intime,
        outtime,
        starttime,
        COALESCE(
            LEAD(starttime) OVER (PARTITION BY stay_id_str ORDER BY starttime),
            outtime + INTERVAL 2 HOURS
        ) AS endtime,
        weight,
        weight_type
    FROM wt_stg2
), wt1 AS (
    SELECT
        stay_id_str,
        starttime,
        COALESCE(
            endtime,
            LEAD(starttime) OVER (PARTITION BY stay_id_str ORDER BY starttime),
            outtime + INTERVAL 2 HOURS
        ) AS endtime,
        weight,
        weight_type
    FROM wt_stg3
), wt_fix AS (
    SELECT
        i.stay_id_str,
        i.intime - INTERVAL 2 HOURS AS starttime,
        w.starttime AS endtime,
        w.weight,
        w.weight_type
    FROM icu_stays i
    INNER JOIN (
        SELECT
            w1.stay_id_str,
            w1.starttime,
            w1.weight,
            w1.weight_type,
            ROW_NUMBER() OVER (
                PARTITION BY w1.stay_id_str ORDER BY w1.starttime
            ) AS rn
        FROM wt1 w1
    ) w
        ON i.stay_id_str = w.stay_id_str
        AND w.rn = 1
        AND i.intime < w.starttime
), final_rows AS (
    SELECT
        stay_id_str,
        starttime,
        endtime,
        weight,
        weight_type
    FROM wt1
    UNION ALL
    SELECT
        stay_id_str,
        starttime,
        endtime,
        weight,
        weight_type
    FROM wt_fix
)
SELECT
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(starttime AS TIMESTAMP_NTZ) AS starttime,
    CAST(endtime AS TIMESTAMP_NTZ) AS endtime,
    CAST(weight AS DECIMAL(38,3)) AS weight,
    CAST(weight_type AS VARCHAR(255)) AS weight_type
FROM final_rows
;
