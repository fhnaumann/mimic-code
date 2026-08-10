SELECT
    CAST(p.subject_id_str AS INTEGER) AS subject_id,
    CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(m.drug_name AS VARCHAR(255)) AS acei,
    CAST(
        TRY_TO_TIMESTAMP(
            REGEXP_REPLACE(
                mr.starttime_str,
                '(Z|[+-][0-9]{2}:[0-9]{2})$',
                ''
            ),
            "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
        ) AS TIMESTAMP_NTZ
    ) AS starttime,
    CAST(
        TRY_TO_TIMESTAMP(
            REGEXP_REPLACE(
                mr.stoptime_str,
                '(Z|[+-][0-9]{2}:[0-9]{2})$',
                ''
            ),
            "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
        ) AS TIMESTAMP_NTZ
    ) AS stoptime
FROM medication_request mr
INNER JOIN medication m
    ON mr.medication_key = m.medication_key
INNER JOIN patient p
    ON mr.patient_key = p.patient_key
INNER JOIN encounter e
    ON mr.encounter_key = e.encounter_key
WHERE mr.pharmacy_id_str IS NOT NULL
    AND mr.medication_key IS NOT NULL
    AND e.hadm_id_str IS NOT NULL
    AND m.drug_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name'
    AND (
        UPPER(m.drug_name) LIKE '%BENAZEPRIL%'
        OR UPPER(m.drug_name) LIKE '%CAPTOPRIL%'
        OR UPPER(m.drug_name) LIKE '%ENALAPRIL%'
        OR UPPER(m.drug_name) LIKE '%FOSINOPRIL%'
        OR UPPER(m.drug_name) LIKE '%LISINOPRIL%'
        OR UPPER(m.drug_name) LIKE '%MOEXIPRIL%'
        OR UPPER(m.drug_name) LIKE '%PERINDOPRIL%'
        OR UPPER(m.drug_name) LIKE '%QUINAPRIL%'
        OR UPPER(m.drug_name) LIKE '%RAMIPRIL%'
        OR UPPER(m.drug_name) LIKE '%TRANDOLAPRIL%'
    )
;
