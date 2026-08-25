WITH icu_encounters AS (
    SELECT
        icu_encounter_key,
        patient_key,
        parent_encounter_key,
        stay_id_str
    FROM icustay_times_icu_encounter
    WHERE stay_id_str IS NOT NULL
), hospital_encounters AS (
    SELECT
        encounter_key,
        hadm_id_str
    FROM icustay_times_hospital_encounter
    WHERE hadm_id_str IS NOT NULL
), patient_ids AS (
    SELECT
        patient_key,
        subject_id_str
    FROM icustay_times_patient
    WHERE subject_id_str IS NOT NULL
), heart_rate_times AS (
    SELECT
        i.stay_id_str,
        MIN(TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)) AS intime_hr,
        MAX(TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)) AS outtime_hr
    FROM icustay_times_observation o
    INNER JOIN icu_encounters i
        ON o.icu_encounter_key = i.icu_encounter_key
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
      AND o.item_code = '220045'
    GROUP BY i.stay_id_str
)
SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(h.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(i.stay_id_str AS INTEGER) AS stay_id,
    CAST(hr.intime_hr AS TIMESTAMP_NTZ) AS intime_hr,
    CAST(hr.outtime_hr AS TIMESTAMP_NTZ) AS outtime_hr,
    p.patient_key AS patient_key,
    h.encounter_key AS encounter_key,
    i.icu_encounter_key AS icu_encounter_key
FROM icu_encounters i
LEFT JOIN hospital_encounters h
    ON i.parent_encounter_key = h.encounter_key
LEFT JOIN patient_ids p
    ON i.patient_key = p.patient_key
LEFT JOIN heart_rate_times hr
    ON i.stay_id_str = hr.stay_id_str
;
