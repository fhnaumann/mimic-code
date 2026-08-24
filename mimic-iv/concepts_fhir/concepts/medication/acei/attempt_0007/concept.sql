WITH acei_medication AS (
    SELECT
        medication_key,
        drug_system,
        drug_name
    FROM medication
    WHERE drug_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name'
        AND (
            UPPER(drug_name) LIKE '%BENAZEPRIL%'
            OR UPPER(drug_name) LIKE '%CAPTOPRIL%'
            OR UPPER(drug_name) LIKE '%ENALAPRIL%'
            OR UPPER(drug_name) LIKE '%FOSINOPRIL%'
            OR UPPER(drug_name) LIKE '%LISINOPRIL%'
            OR UPPER(drug_name) LIKE '%MOEXIPRIL%'
            OR UPPER(drug_name) LIKE '%PERINDOPRIL%'
            OR UPPER(drug_name) LIKE '%QUINAPRIL%'
            OR UPPER(drug_name) LIKE '%RAMIPRIL%'
            OR UPPER(drug_name) LIKE '%TRANDOLAPRIL%'
        )
), prescription_rows AS (
    SELECT
        p.subject_id_str,
        p.patient_key,
        e.hadm_id_str,
        e.encounter_key,
        m.drug_name AS acei_str,
        mr.starttime_str,
        mr.stoptime_str
    FROM medication_request mr
    INNER JOIN acei_medication m
        ON mr.medication_key = m.medication_key
    INNER JOIN patient p
        ON mr.patient_key = p.patient_key
    INNER JOIN encounter e
        ON mr.encounter_key = e.encounter_key
    WHERE mr.pharmacy_id_str IS NOT NULL
        AND mr.medication_key IS NOT NULL
        AND e.hadm_id_str IS NOT NULL

    UNION ALL

    SELECT
        p.subject_id_str,
        p.patient_key,
        e.hadm_id_str,
        e.encounter_key,
        m.drug_name AS acei_str,
        mr.starttime_str,
        mr.stoptime_str
    FROM medication_request mr
    INNER JOIN medication_mix mm
        ON mr.medication_key = mm.mix_key
    INNER JOIN acei_medication m
        ON mm.ingredient_medication_key = m.medication_key
    INNER JOIN patient p
        ON mr.patient_key = p.patient_key
    INNER JOIN encounter e
        ON mr.encounter_key = e.encounter_key
    WHERE mr.pharmacy_id_str IS NOT NULL
        AND mr.medication_key IS NOT NULL
        AND e.hadm_id_str IS NOT NULL
), parsed_rows AS (
    SELECT
        subject_id_str,
        patient_key,
        hadm_id_str,
        encounter_key,
        acei_str,
        TRY_CAST(starttime_str AS TIMESTAMP_NTZ) AS starttime_ts,
        TRY_CAST(stoptime_str AS TIMESTAMP_NTZ) AS stoptime_ts
    FROM prescription_rows
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    patient_key,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    encounter_key,
    CAST(acei_str AS VARCHAR(255)) AS acei,
    CAST(starttime_ts AS TIMESTAMP_NTZ) AS starttime,
    CAST(stoptime_ts AS TIMESTAMP_NTZ) AS stoptime
FROM parsed_rows
;
