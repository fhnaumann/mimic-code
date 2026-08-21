WITH icu_stays AS (
    SELECT
        p.subject_id_str,
        e.stay_id_str,
        TRY_CAST(e.intime_datetime AS TIMESTAMP_NTZ) AS intime,
        p.patient_key,
        e.icu_encounter_key
    FROM icu_encounter e
    LEFT JOIN patient p
        ON e.patient_key = p.patient_key
    WHERE e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
        AND e.stay_id_str IS NOT NULL
), gcs_final AS (
    SELECT
        i.subject_id_str,
        i.stay_id_str,
        i.patient_key,
        i.icu_encounter_key,
        g.charttime,
        g.gcs,
        g.gcs_motor,
        g.gcs_verbal,
        g.gcs_eyes,
        ROW_NUMBER() OVER (
            PARTITION BY g.icu_encounter_key
            ORDER BY g.gcs ASC NULLS LAST, g.charttime DESC NULLS LAST
        ) AS gcs_seq
    FROM icu_stays i
    LEFT JOIN gcs g
        ON i.icu_encounter_key = g.icu_encounter_key
        AND g.charttime >= i.intime - INTERVAL 6 HOURS
        AND g.charttime <= i.intime + INTERVAL 1 DAY
)
SELECT
    CAST(i.subject_id_str AS INTEGER) AS subject_id,
    CAST(i.stay_id_str AS INTEGER) AS stay_id,
    CAST(gs.gcs AS FLOAT) AS gcs_min,
    CAST(gs.gcs_motor AS FLOAT) AS gcs_motor,
    CAST(gs.gcs_verbal AS FLOAT) AS gcs_verbal,
    CAST(gs.gcs_eyes AS FLOAT) AS gcs_eyes,
    CAST(NULL AS INTEGER) AS gcs_unable,
    i.patient_key AS patient_key,
    i.icu_encounter_key AS icu_encounter_key
FROM icu_stays i
LEFT JOIN gcs_final gs
    ON i.icu_encounter_key = gs.icu_encounter_key
    AND gs.gcs_seq = 1
;
