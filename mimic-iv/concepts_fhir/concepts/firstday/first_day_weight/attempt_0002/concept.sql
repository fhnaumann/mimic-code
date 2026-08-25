WITH icu AS (
    SELECT
        CAST(p.subject_id_str AS INTEGER) AS subject_id,
        CAST(e.stay_id_str AS INTEGER) AS stay_id,
        TRY_CAST(e.intime_datetime AS TIMESTAMP_NTZ) AS intime,
        p.patient_key AS patient_key,
        e.icu_encounter_key AS icu_encounter_key
    FROM icu_encounter e
    LEFT JOIN patient p
        ON e.patient_key = p.patient_key
    WHERE e.stay_id_str IS NOT NULL
), aggregated AS (
    SELECT
        i.subject_id,
        i.stay_id,
        AVG(CASE WHEN ce.weight_type = 'admit' THEN ce.weight ELSE NULL END) AS weight_admit,
        AVG(ce.weight) AS weight,
        MIN(ce.weight) AS weight_min,
        MAX(ce.weight) AS weight_max,
        i.icu_encounter_key,
        i.patient_key
    FROM icu i
    LEFT JOIN weight_durations ce
        ON i.icu_encounter_key = ce.icu_encounter_key
        AND ce.starttime <= i.intime + INTERVAL 1 DAY
    GROUP BY
        i.subject_id,
        i.stay_id,
        i.icu_encounter_key,
        i.patient_key
)
SELECT
    CAST(a.subject_id AS INTEGER) AS subject_id,
    CAST(a.stay_id AS INTEGER) AS stay_id,
    CAST(a.weight_admit AS DOUBLE) AS weight_admit,
    CAST(a.weight AS DOUBLE) AS weight,
    CAST(a.weight_min AS DECIMAL(38,3)) AS weight_min,
    CAST(a.weight_max AS DECIMAL(38,3)) AS weight_max,
    a.icu_encounter_key AS icu_encounter_key,
    a.patient_key AS patient_key
FROM aggregated a
;
