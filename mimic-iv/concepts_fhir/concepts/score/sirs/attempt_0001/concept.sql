WITH icu_stays AS (
    SELECT
        e.icu_encounter_key,
        e.patient_key,
        e.encounter_key,
        e.stay_id_str
    FROM icu_encounter e
    WHERE e.stay_id_str IS NOT NULL
), hospital_encounters AS (
    SELECT
        e.encounter_key,
        e.hadm_id_str
    FROM encounter e
    WHERE e.hadm_id_str IS NOT NULL
), scorecomp AS (
    SELECT
        i.icu_encounter_key,
        i.patient_key,
        i.encounter_key,
        i.stay_id_str,
        v.temperature_min,
        v.temperature_max,
        v.heart_rate_max,
        v.resp_rate_max,
        bg.pco2_min AS paco2_min,
        l.wbc_min,
        l.wbc_max,
        l.bands_max
    FROM icu_stays i
    LEFT JOIN first_day_bg_art bg
        ON i.icu_encounter_key = bg.icu_encounter_key
    LEFT JOIN first_day_vitalsign v
        ON i.icu_encounter_key = v.icu_encounter_key
    LEFT JOIN first_day_lab l
        ON i.icu_encounter_key = l.icu_encounter_key
), scorecalc AS (
    SELECT
        icu_encounter_key,
        patient_key,
        encounter_key,
        stay_id_str,
        CASE
            WHEN temperature_min < 36.0 THEN 1
            WHEN temperature_max > 38.0 THEN 1
            WHEN temperature_min IS NULL THEN NULL
            ELSE 0
        END AS temp_score,
        CASE
            WHEN heart_rate_max > 90.0 THEN 1
            WHEN heart_rate_max IS NULL THEN NULL
            ELSE 0
        END AS heart_rate_score,
        CASE
            WHEN resp_rate_max > 20.0 THEN 1
            WHEN paco2_min < 32.0 THEN 1
            WHEN COALESCE(resp_rate_max, paco2_min) IS NULL THEN NULL
            ELSE 0
        END AS resp_score,
        CASE
            WHEN wbc_min < 4.0 THEN 1
            WHEN wbc_max > 12.0 THEN 1
            WHEN bands_max > 10 THEN 1
            WHEN COALESCE(wbc_min, bands_max) IS NULL THEN NULL
            ELSE 0
        END AS wbc_score
    FROM scorecomp
), identity_spine AS (
    SELECT
        i.icu_encounter_key,
        i.patient_key,
        i.encounter_key,
        i.stay_id_str,
        p.subject_id_str,
        h.hadm_id_str
    FROM icu_stays i
    LEFT JOIN patient p
        ON i.patient_key = p.patient_key
    LEFT JOIN hospital_encounters h
        ON i.encounter_key = h.encounter_key
)
SELECT
    CAST(r.subject_id_str AS INTEGER) AS subject_id,
    CAST(r.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(r.stay_id_str AS INTEGER) AS stay_id,
    CAST(
        COALESCE(s.temp_score, 0)
        + COALESCE(s.heart_rate_score, 0)
        + COALESCE(s.resp_score, 0)
        + COALESCE(s.wbc_score, 0)
        AS INTEGER
    ) AS sirs,
    CAST(s.temp_score AS INTEGER) AS temp_score,
    CAST(s.heart_rate_score AS INTEGER) AS heart_rate_score,
    CAST(s.resp_score AS INTEGER) AS resp_score,
    CAST(s.wbc_score AS INTEGER) AS wbc_score,
    r.encounter_key AS encounter_key,
    r.icu_encounter_key AS icu_encounter_key,
    r.patient_key AS patient_key
FROM identity_spine r
LEFT JOIN scorecalc s
    ON r.icu_encounter_key = s.icu_encounter_key
;
