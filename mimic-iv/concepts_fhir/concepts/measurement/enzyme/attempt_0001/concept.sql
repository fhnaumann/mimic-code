WITH filtered_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        s.specimen_id_str,
        l.code,
        l.system,
        l.effective_datetime,
        l.effective_period_start,
        l.quantity_value,
        l.quantity_comparator,
        l.value_string
    FROM lab_observation l
    INNER JOIN patient p
        ON l.patient_key = p.patient_key
    INNER JOIN specimen s
        ON l.specimen_key = s.specimen_key
    LEFT JOIN encounter e
        ON l.encounter_key = e.encounter_key
    WHERE l.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems'
        AND l.code IN (
            '50861', '50863', '50878', '50867', '50885', '50883',
            '50884', '50910', '50911', '50927', '50954'
        )
        AND l.quantity_value IS NOT NULL
        AND l.quantity_comparator IS NULL
        AND l.value_string IS NULL
), typed_rows AS (
    SELECT
        CAST(subject_id_str AS INTEGER) AS subject_id,
        CAST(hadm_id_str AS INTEGER) AS hadm_id,
        CAST(specimen_id_str AS INTEGER) AS specimen_id,
        code,
        CAST(quantity_value AS DOUBLE) AS value_num,
        COALESCE(
            COALESCE(
                TRY_CAST(effective_datetime AS TIMESTAMP_NTZ),
                CAST(
                    TRY_TO_TIMESTAMP(
                        regexp_replace(
                            regexp_replace(effective_datetime, '(Z|[+-][0-9]{2}:[0-9]{2})$', ''),
                            'T',
                            ' '
                        ),
                        'yyyy-MM-dd HH:mm:ss'
                    ) AS TIMESTAMP_NTZ
                )
            ),
            COALESCE(
                TRY_CAST(effective_period_start AS TIMESTAMP_NTZ),
                CAST(
                    TRY_TO_TIMESTAMP(
                        regexp_replace(
                            regexp_replace(effective_period_start, '(Z|[+-][0-9]{2}:[0-9]{2})$', ''),
                            'T',
                            ' '
                        ),
                        'yyyy-MM-dd HH:mm:ss'
                    ) AS TIMESTAMP_NTZ
                )
            )
        ) AS charttime
    FROM filtered_rows
), eligible_rows AS (
    SELECT
        subject_id,
        hadm_id,
        specimen_id,
        code,
        charttime,
        value_num
    FROM typed_rows
    WHERE value_num > 0
), grouped AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(CASE WHEN code = '50861' THEN value_num ELSE NULL END) AS alt,
        MAX(CASE WHEN code = '50863' THEN value_num ELSE NULL END) AS alp,
        MAX(CASE WHEN code = '50878' THEN value_num ELSE NULL END) AS ast,
        MAX(CASE WHEN code = '50867' THEN value_num ELSE NULL END) AS amylase,
        MAX(CASE WHEN code = '50885' THEN value_num ELSE NULL END) AS bilirubin_total,
        MAX(CASE WHEN code = '50883' THEN value_num ELSE NULL END) AS bilirubin_direct,
        MAX(CASE WHEN code = '50884' THEN value_num ELSE NULL END) AS bilirubin_indirect,
        MAX(CASE WHEN code = '50910' THEN value_num ELSE NULL END) AS ck_cpk,
        MAX(CASE WHEN code = '50911' THEN value_num ELSE NULL END) AS ck_mb,
        MAX(CASE WHEN code = '50927' THEN value_num ELSE NULL END) AS ggt,
        MAX(CASE WHEN code = '50954' THEN value_num ELSE NULL END) AS ld_ldh
    FROM eligible_rows
    GROUP BY specimen_id
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    CAST(alt AS DOUBLE) AS alt,
    CAST(alp AS DOUBLE) AS alp,
    CAST(ast AS DOUBLE) AS ast,
    CAST(amylase AS DOUBLE) AS amylase,
    CAST(bilirubin_total AS DOUBLE) AS bilirubin_total,
    CAST(bilirubin_direct AS DOUBLE) AS bilirubin_direct,
    CAST(bilirubin_indirect AS DOUBLE) AS bilirubin_indirect,
    CAST(ck_cpk AS DOUBLE) AS ck_cpk,
    CAST(ck_mb AS DOUBLE) AS ck_mb,
    CAST(ggt AS DOUBLE) AS ggt,
    CAST(ld_ldh AS DOUBLE) AS ld_ldh
FROM grouped
;
