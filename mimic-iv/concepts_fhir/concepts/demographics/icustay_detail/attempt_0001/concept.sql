WITH icu_encounters AS (
    SELECT
        encounter_key AS icu_encounter_key,
        patient_key,
        parent_encounter_key,
        stay_id_str,
        TRY_CAST(period_start AS TIMESTAMP_NTZ) AS icu_intime,
        TRY_CAST(period_end AS TIMESTAMP_NTZ) AS icu_outtime
    FROM icustay_detail_icu_encounter
    WHERE stay_id_str IS NOT NULL
), hospital_encounters AS (
    SELECT
        encounter_key AS hospital_encounter_key,
        hadm_id_str,
        TRY_CAST(period_start AS TIMESTAMP_NTZ) AS hospital_admittime,
        TRY_CAST(period_end AS TIMESTAMP_NTZ) AS hospital_dischtime
    FROM icustay_detail_hospital_encounter
    WHERE hadm_id_str IS NOT NULL
), joined_rows AS (
    SELECT
        i.stay_id_str,
        h.hadm_id_str,
        p.subject_id_str,
        p.patient_key AS resolved_patient_key,
        h.hospital_encounter_key,
        h.hospital_admittime,
        h.hospital_dischtime,
        i.icu_intime,
        i.icu_outtime,
        TRY_CAST(p.birth_date AS DATE) AS birth_date,
        TRY_CAST(p.dod_datetime AS TIMESTAMP_NTZ) AS dod_datetime,
        CASE
            WHEN LOWER(p.gender) = 'male' THEN 'M'
            WHEN LOWER(p.gender) = 'female' THEN 'F'
            ELSE p.gender
        END AS gender,
        CASE p.race_text
            WHEN 'Black or African American' THEN 'BLACK/AFRICAN AMERICAN'
            WHEN 'White' THEN 'WHITE'
            WHEN 'asked but unknown' THEN 'PATIENT DECLINED TO ANSWER'
            WHEN 'unknown' THEN 'UNKNOWN'
            ELSE p.race_text
        END AS race
    FROM icu_encounters i
    LEFT JOIN hospital_encounters h
        ON i.parent_encounter_key = h.hospital_encounter_key
    LEFT JOIN icustay_detail_patient p
        ON i.patient_key = p.patient_key
), ranked_rows AS (
    SELECT
        j.*,
        DENSE_RANK() OVER (
            PARTITION BY j.subject_id_str
            ORDER BY j.hospital_admittime NULLS FIRST
        ) AS hospstay_seq,
        DENSE_RANK() OVER (
            PARTITION BY j.hadm_id_str
            ORDER BY j.icu_intime NULLS FIRST
        ) AS icustay_seq
    FROM joined_rows j
), derived_rows AS (
    SELECT
        subject_id_str,
        hadm_id_str,
        stay_id_str,
        gender,
        dod_datetime,
        hospital_admittime AS admittime,
        hospital_dischtime AS dischtime,
        DATEDIFF(TO_DATE(hospital_dischtime), TO_DATE(hospital_admittime)) AS los_hospital,
        YEAR(hospital_admittime) - YEAR(birth_date) AS admission_age,
        race,
        CASE
            WHEN hospital_encounter_key IS NULL OR resolved_patient_key IS NULL THEN NULL
            WHEN dod_datetime IS NOT NULL
                AND TO_DATE(dod_datetime) >= TO_DATE(hospital_admittime)
                AND TO_DATE(dod_datetime) <= TO_DATE(hospital_dischtime)
                THEN 1
            ELSE 0
        END AS hospital_expire_flag,
        CASE WHEN hospital_admittime IS NULL THEN NULL ELSE hospstay_seq END AS hospstay_seq,
        CASE
            WHEN hospital_admittime IS NULL THEN NULL
            WHEN hospstay_seq = 1 THEN TRUE
            ELSE FALSE
        END AS first_hosp_stay,
        icu_intime,
        icu_outtime,
        ROUND(
            CAST((
                DATEDIFF(TO_DATE(icu_outtime), TO_DATE(icu_intime)) * 24
                + HOUR(icu_outtime) - HOUR(icu_intime)
            ) / 24.0 AS DECIMAL(38,9)),
            2
        ) AS los_icu,
        icustay_seq,
        CASE WHEN icustay_seq = 1 THEN TRUE ELSE FALSE END AS first_icu_stay
    FROM ranked_rows
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(gender AS VARCHAR(255)) AS gender,
    CAST(dod_datetime AS DATE) AS dod,
    CAST(admittime AS TIMESTAMP_NTZ) AS admittime,
    CAST(dischtime AS TIMESTAMP_NTZ) AS dischtime,
    CAST(los_hospital AS BIGINT) AS los_hospital,
    CAST(admission_age AS BIGINT) AS admission_age,
    CAST(race AS VARCHAR(255)) AS race,
    CAST(hospital_expire_flag AS SMALLINT) AS hospital_expire_flag,
    CAST(hospstay_seq AS BIGINT) AS hospstay_seq,
    CAST(first_hosp_stay AS BOOLEAN) AS first_hosp_stay,
    CAST(icu_intime AS TIMESTAMP_NTZ) AS icu_intime,
    CAST(icu_outtime AS TIMESTAMP_NTZ) AS icu_outtime,
    CAST(los_icu AS DECIMAL(38,2)) AS los_icu,
    CAST(icustay_seq AS BIGINT) AS icustay_seq,
    CAST(first_icu_stay AS BOOLEAN) AS first_icu_stay
FROM derived_rows
;
