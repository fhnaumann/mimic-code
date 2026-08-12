WITH filtered_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        s.specimen_id_str,
        l.effective_datetime,
        l.quantity_value,
        l.quantity_comparator,
        l.value_string
    FROM lab_observation l
    LEFT JOIN patient p
        ON l.patient_key = p.patient_key
    LEFT JOIN specimen s
        ON l.specimen_key = s.specimen_key
    LEFT JOIN encounter e
        ON l.encounter_key = e.encounter_key
    WHERE l.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems'
        AND l.code = '50889'
        AND l.quantity_value IS NOT NULL
        AND l.quantity_comparator IS NULL
        AND l.value_string IS NULL
), typed_rows AS (
    SELECT
        CAST(subject_id_str AS INTEGER) AS subject_id,
        CAST(hadm_id_str AS INTEGER) AS hadm_id,
        TRY_CAST(effective_datetime AS TIMESTAMP_NTZ) AS charttime,
        CAST(specimen_id_str AS INTEGER) AS specimen_id,
        CAST(quantity_value AS DOUBLE) AS value_num
    FROM filtered_rows
    WHERE CAST(quantity_value AS DOUBLE) > 0
), grouped AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(value_num) AS crp
    FROM typed_rows
    GROUP BY specimen_id
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    CAST(crp AS DOUBLE) AS crp
FROM grouped
;
