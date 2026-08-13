WITH heart_rate_times AS (
    SELECT
        i.stay_id_str,
        MIN(TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)) AS intime_hr,
        MAX(TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)) AS outtime_hr
    FROM icustay_times_observation o
    INNER JOIN icustay_times_icu_encounter i
        ON o.encounter_key = i.encounter_key
    WHERE i.stay_id_str IS NOT NULL
      AND o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
      AND o.item_code = '220045'
    GROUP BY i.stay_id_str
)
SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(h.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(i.stay_id_str AS INTEGER) AS stay_id,
    CAST(hr.intime_hr AS TIMESTAMP_NTZ) AS intime_hr,
    CAST(hr.outtime_hr AS TIMESTAMP_NTZ) AS outtime_hr
FROM icustay_times_icu_encounter i
LEFT JOIN icustay_times_hospital_encounter h
    ON i.parent_encounter_key = h.encounter_key
LEFT JOIN icustay_times_patient p
    ON i.patient_key = p.patient_key
LEFT JOIN heart_rate_times hr
    ON i.stay_id_str = hr.stay_id_str
WHERE i.stay_id_str IS NOT NULL
;
