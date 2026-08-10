SELECT
    p.subject_id AS subject_id,
    e.hadm_id AS hadm_id,
    CAST(e.admittime AS TIMESTAMP_NTZ) AS admittime,
    CAST(NULL AS SMALLINT) AS anchor_age,
    CAST(NULL AS SMALLINT) AS anchor_year,
    CAST(
        YEAR(CAST(e.admittime AS TIMESTAMP_NTZ))
        - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ))
        AS INTEGER
    ) AS age
FROM patient AS p
INNER JOIN encounter AS e
    ON p.subject_id = e.subject_id
