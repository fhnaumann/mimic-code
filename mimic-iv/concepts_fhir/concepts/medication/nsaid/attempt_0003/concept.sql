WITH medication_names AS (
    SELECT
        medication_key,
        drug_name AS drug
    FROM medication
    WHERE drug_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name'
), nsaid_drug AS (
    SELECT DISTINCT
        medication_key,
        drug,
        CASE
            WHEN UPPER(drug) LIKE '%ASPIRIN%' THEN 1
            WHEN UPPER(drug) LIKE '%BROMFENAC%' THEN 1
            WHEN UPPER(drug) LIKE '%CELECOXIB%' THEN 1
            WHEN UPPER(drug) LIKE '%DICLOFENAC%' THEN 1
            WHEN UPPER(drug) LIKE '%DIFLUNISAL%' THEN 1
            WHEN UPPER(drug) LIKE '%ETODOLAC%' THEN 1
            WHEN UPPER(drug) LIKE '%FENOPROFEN%' THEN 1
            WHEN UPPER(drug) LIKE '%FLURBIPROFEN%' THEN 1
            WHEN UPPER(drug) LIKE '%IBUPROFEN%' THEN 1
            WHEN UPPER(drug) LIKE '%INDOMETHACIN%' THEN 1
            WHEN UPPER(drug) LIKE '%KETOPROFEN%' THEN 1
            WHEN UPPER(drug) LIKE '%MEFENAMIC ACID%' THEN 1
            WHEN UPPER(drug) LIKE '%MELOXICAM%' THEN 1
            WHEN UPPER(drug) LIKE '%NABUMETONE%' THEN 1
            WHEN UPPER(drug) LIKE '%NAPROXEN%' THEN 1
            WHEN UPPER(drug) LIKE '%NEPAFENAC%' THEN 1
            WHEN UPPER(drug) LIKE '%OXAPROZIN%' THEN 1
            WHEN UPPER(drug) LIKE '%PIROXICAM%' THEN 1
            WHEN UPPER(drug) LIKE '%SULINDAC%' THEN 1
            WHEN UPPER(drug) LIKE '%TOLMETIN%' THEN 1
            ELSE 0
        END AS nsaid
    FROM medication_names
), prescription_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        d.drug AS nsaid_str,
        mr.starttime_str,
        mr.stoptime_str,
        p.patient_key,
        e.encounter_key
    FROM medication_request mr
    INNER JOIN nsaid_drug d
        ON mr.medication_key = d.medication_key
    INNER JOIN patient p
        ON mr.patient_key = p.patient_key
    INNER JOIN encounter e
        ON mr.encounter_key = e.encounter_key
    WHERE mr.pharmacy_id_str IS NOT NULL
        AND mr.medication_key IS NOT NULL
        AND d.nsaid = 1
        AND e.hadm_id_str IS NOT NULL

    UNION ALL

    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        d.drug AS nsaid_str,
        mr.starttime_str,
        mr.stoptime_str,
        p.patient_key,
        e.encounter_key
    FROM medication_request mr
    INNER JOIN medication_mix mm
        ON mr.medication_key = mm.mix_key
    INNER JOIN medication_mix_ingredient mi
        ON mm.mix_key = mi.mix_key
    INNER JOIN nsaid_drug d
        ON mi.ingredient_medication_key = d.medication_key
    INNER JOIN patient p
        ON mr.patient_key = p.patient_key
    INNER JOIN encounter e
        ON mr.encounter_key = e.encounter_key
    WHERE mr.pharmacy_id_str IS NOT NULL
        AND mr.medication_key IS NOT NULL
        AND mm.mix_system = 'http://mimic.mit.edu/fhir/mimic/identifier/medication-mix'
        AND d.nsaid = 1
        AND e.hadm_id_str IS NOT NULL
), parsed_rows AS (
    SELECT
        subject_id_str,
        hadm_id_str,
        nsaid_str,
        TRY_CAST(starttime_str AS TIMESTAMP_NTZ) AS starttime_ts,
        TRY_CAST(stoptime_str AS TIMESTAMP_NTZ) AS stoptime_ts,
        patient_key,
        encounter_key
    FROM prescription_rows
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    patient_key,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    encounter_key,
    CAST(nsaid_str AS VARCHAR(255)) AS nsaid,
    CAST(starttime_ts AS TIMESTAMP_NTZ) AS starttime,
    CAST(stoptime_ts AS TIMESTAMP_NTZ) AS stoptime
FROM parsed_rows
;
