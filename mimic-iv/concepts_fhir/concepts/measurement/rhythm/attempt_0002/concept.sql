WITH observation_rows AS (
    SELECT
        o.patient_key,
        o.encounter_key,
        o.effective_datetime,
        o.item_code,
        o.item_system,
        o.value_string
    FROM rhythm_observation o
    WHERE o.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND o.item_code IN ('220048', '224650', '224651', '226479', '226480')
), typed_rows AS (
    SELECT
        p.subject_id_str,
        e.stay_id_str,
        TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ) AS charttime,
        o.item_code,
        o.value_string
    FROM observation_rows o
    INNER JOIN rhythm_patient p
        ON o.patient_key = p.patient_key
    INNER JOIN rhythm_encounter e
        ON o.encounter_key = e.encounter_key
    WHERE e.stay_id_str IS NOT NULL
), pivoted AS (
    SELECT
        subject_id_str,
        charttime,
        CASE
            WHEN COUNT(CASE WHEN item_code = '220048' AND value_string IS NOT NULL THEN 1 END) = 0
                THEN NULL
            ELSE concat_ws(
                '; ',
                sort_array(collect_set(
                    CASE WHEN item_code = '220048' THEN value_string END
                ))
            )
        END AS heart_rhythm,
        MAX(CASE WHEN item_code = '224650' THEN value_string END) AS ectopy_type,
        MAX(CASE WHEN item_code = '224651' THEN value_string END) AS ectopy_frequency,
        MAX(CASE WHEN item_code = '226479' THEN value_string END) AS ectopy_type_secondary,
        MAX(CASE WHEN item_code = '226480' THEN value_string END) AS ectopy_frequency_secondary
    FROM typed_rows
    GROUP BY subject_id_str, charttime
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(heart_rhythm AS VARCHAR(255)) AS heart_rhythm,
    CAST(ectopy_type AS VARCHAR(255)) AS ectopy_type,
    CAST(ectopy_frequency AS VARCHAR(255)) AS ectopy_frequency,
    CAST(ectopy_type_secondary AS VARCHAR(255)) AS ectopy_type_secondary,
    CAST(ectopy_frequency_secondary AS VARCHAR(255)) AS ectopy_frequency_secondary
FROM pivoted;
