WITH arb_medication AS (
    SELECT
        medication_key,
        drug_system,
        drug_name
    FROM medication
    WHERE drug_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name'
        AND (
            UPPER(drug_name) LIKE '%AZILSARTAN%'
            OR UPPER(drug_name) LIKE '%EDARBI%'
            OR UPPER(drug_name) LIKE '%CANDESARTAN%'
            OR UPPER(drug_name) LIKE '%ATACAND%'
            OR UPPER(drug_name) LIKE '%IRBESARTAN%'
            OR UPPER(drug_name) LIKE '%AVAPRO%'
            OR UPPER(drug_name) LIKE '%LOSARTAN%'
            OR UPPER(drug_name) LIKE '%COZAAR%'
            OR UPPER(drug_name) LIKE '%OLMESARTAN%'
            OR UPPER(drug_name) LIKE '%BENICAR%'
            OR UPPER(drug_name) LIKE '%TELMISARTAN%'
            OR UPPER(drug_name) LIKE '%MICARDIS%'
            OR UPPER(drug_name) LIKE '%VALSARTAN%'
            OR UPPER(drug_name) LIKE '%DIOVAN%'
            OR UPPER(drug_name) LIKE '%SACUBITRIL%'
            OR UPPER(drug_name) LIKE '%ENTRESTO%'
        )
), prescription_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        m.drug_name AS arb_str,
        mr.starttime_str,
        mr.stoptime_str,
        p.patient_key,
        e.encounter_key
    FROM medication_request mr
    INNER JOIN arb_medication m
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
        e.hadm_id_str,
        m.drug_name AS arb_str,
        mr.starttime_str,
        mr.stoptime_str,
        p.patient_key,
        e.encounter_key
    FROM medication_request mr
    INNER JOIN medication_mix mm
        ON mr.medication_key = mm.mix_key
    INNER JOIN medication_mix_ingredient mi
        ON mm.mix_key = mi.mix_key
    INNER JOIN arb_medication m
        ON mi.ingredient_medication_key = m.medication_key
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
        hadm_id_str,
        arb_str,
        TRY_CAST(starttime_str AS TIMESTAMP_NTZ) AS starttime_ts,
        TRY_CAST(stoptime_str AS TIMESTAMP_NTZ) AS stoptime_ts,
        patient_key,
        encounter_key
    FROM prescription_rows
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    CAST(arb_str AS VARCHAR(255)) AS arb,
    CAST(starttime_ts AS TIMESTAMP_NTZ) AS starttime,
    CAST(stoptime_ts AS TIMESTAMP_NTZ) AS stoptime,
    encounter_key,
    patient_key
FROM parsed_rows
;
