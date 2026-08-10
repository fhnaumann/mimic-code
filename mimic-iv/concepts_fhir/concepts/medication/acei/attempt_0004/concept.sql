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
        e.hadm_id_str,
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
        e.hadm_id_str,
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
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    CAST(acei_str AS VARCHAR(255)) AS acei,
    CAST(
        TRY_TO_TIMESTAMP(
            REGEXP_REPLACE(
                starttime_str,
                '(Z|[+-][0-9]{2}:[0-9]{2})$',
                ''
            ),
            "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
        ) AS TIMESTAMP_NTZ
    ) AS starttime,
    CAST(
        TRY_TO_TIMESTAMP(
            REGEXP_REPLACE(
                stoptime_str,
                '(Z|[+-][0-9]{2}:[0-9]{2})$',
                ''
            ),
            "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
        ) AS TIMESTAMP_NTZ
    ) AS stoptime
FROM prescription_rows
;
