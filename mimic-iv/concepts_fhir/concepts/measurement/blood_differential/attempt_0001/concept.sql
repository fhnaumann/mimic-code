WITH lab_rows AS (
    SELECT
        CAST(p.subject_id_str AS INTEGER) AS subject_id,
        CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
        CAST(
            COALESCE(l.effective_datetime, l.effective_period_start)
            AS TIMESTAMP_NTZ
        ) AS charttime,
        CAST(s.specimen_id_str AS INTEGER) AS specimen_id,
        l.code,
        l.system,
        CAST(l.quantity_value AS DOUBLE) AS quantity_value
    FROM lab_observation l
    INNER JOIN patient p
        ON l.patient_key = p.patient_key
    INNER JOIN specimen s
        ON l.specimen_key = s.specimen_key
    LEFT JOIN encounter e
        ON l.encounter_key = e.encounter_key
    WHERE l.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems'
        AND l.code IN (
            '51146', '52069', '51199', '51200', '52073', '51244', '51245',
            '51133', '52769', '51253', '51254', '52074', '51256', '52075',
            '51143', '51144', '51218', '52135', '51251', '51257', '51300',
            '51301', '51755'
        )
        AND CAST(l.quantity_value AS DOUBLE) IS NOT NULL
        AND CAST(l.quantity_value AS DOUBLE) >= 0
),
blood_diff AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(
            CASE
                WHEN code IN ('51300', '51301', '51755') THEN quantity_value
                ELSE NULL
            END
        ) AS wbc,
        MAX(
            CASE WHEN code = '52069' THEN quantity_value ELSE NULL END
        ) AS basophils_abs,
        MAX(
            CASE
                WHEN code = '52073' THEN quantity_value
                WHEN code = '51199' THEN quantity_value / 1000.0
                ELSE NULL
            END
        ) AS eosinophils_abs,
        MAX(
            CASE
                WHEN code = '51133' THEN quantity_value
                WHEN code = '52769' THEN quantity_value / 1000.0
                ELSE NULL
            END
        ) AS lymphocytes_abs,
        MAX(
            CASE
                WHEN code = '52074' THEN quantity_value
                WHEN code = '51253' THEN quantity_value / 1000.0
                ELSE NULL
            END
        ) AS monocytes_abs,
        MAX(
            CASE WHEN code = '52075' THEN quantity_value ELSE NULL END
        ) AS neutrophils_abs,
        MAX(
            CASE WHEN code = '51218' THEN quantity_value / 1000.0 ELSE NULL END
        ) AS granulocytes_abs,
        MAX(
            CASE WHEN code = '51146' THEN quantity_value ELSE NULL END
        ) AS basophils,
        MAX(
            CASE WHEN code = '51200' THEN quantity_value ELSE NULL END
        ) AS eosinophils,
        MAX(
            CASE WHEN code IN ('51244', '51245') THEN quantity_value ELSE NULL END
        ) AS lymphocytes,
        MAX(
            CASE WHEN code = '51254' THEN quantity_value ELSE NULL END
        ) AS monocytes,
        MAX(
            CASE WHEN code = '51256' THEN quantity_value ELSE NULL END
        ) AS neutrophils,
        MAX(
            CASE WHEN code = '51143' THEN quantity_value ELSE NULL END
        ) AS atypical_lymphocytes,
        MAX(
            CASE WHEN code = '51144' THEN quantity_value ELSE NULL END
        ) AS bands,
        MAX(
            CASE WHEN code = '52135' THEN quantity_value ELSE NULL END
        ) AS immature_granulocytes,
        MAX(
            CASE WHEN code = '51251' THEN quantity_value ELSE NULL END
        ) AS metamyelocytes,
        MAX(
            CASE WHEN code = '51257' THEN quantity_value ELSE NULL END
        ) AS nrbc,
        CASE
            WHEN MAX(
                CASE
                    WHEN code IN ('51300', '51301', '51755') THEN quantity_value
                    ELSE NULL
                END
            ) > 0
            AND SUM(
                CASE
                    WHEN code IN ('51146', '51200', '51244', '51245', '51254', '51256')
                        THEN quantity_value
                    ELSE NULL
                END
            ) > 0
            THEN 1
            ELSE 0
        END AS impute_abs
    FROM lab_rows
    GROUP BY specimen_id
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen_id AS INTEGER) AS specimen_id,
    CAST(wbc AS DOUBLE) AS wbc,
    CAST(
        ROUND(
            CAST(
                CASE
                    WHEN basophils_abs IS NULL
                        AND basophils IS NOT NULL
                        AND impute_abs = 1
                        THEN basophils * wbc / 100
                    ELSE basophils_abs
                END AS DECIMAL(38, 10)
            ),
            4
        ) AS DECIMAL(38, 4)
    ) AS basophils_abs,
    CAST(
        ROUND(
            CAST(
                CASE
                    WHEN eosinophils_abs IS NULL
                        AND eosinophils IS NOT NULL
                        AND impute_abs = 1
                        THEN eosinophils * wbc / 100
                    ELSE eosinophils_abs
                END AS DECIMAL(38, 10)
            ),
            4
        ) AS DECIMAL(38, 4)
    ) AS eosinophils_abs,
    CAST(
        ROUND(
            CAST(
                CASE
                    WHEN lymphocytes_abs IS NULL
                        AND lymphocytes IS NOT NULL
                        AND impute_abs = 1
                        THEN lymphocytes * wbc / 100
                    ELSE lymphocytes_abs
                END AS DECIMAL(38, 10)
            ),
            4
        ) AS DECIMAL(38, 4)
    ) AS lymphocytes_abs,
    CAST(
        ROUND(
            CAST(
                CASE
                    WHEN monocytes_abs IS NULL
                        AND monocytes IS NOT NULL
                        AND impute_abs = 1
                        THEN monocytes * wbc / 100
                    ELSE monocytes_abs
                END AS DECIMAL(38, 10)
            ),
            4
        ) AS DECIMAL(38, 4)
    ) AS monocytes_abs,
    CAST(
        ROUND(
            CAST(
                CASE
                    WHEN neutrophils_abs IS NULL
                        AND neutrophils IS NOT NULL
                        AND impute_abs = 1
                        THEN neutrophils * wbc / 100
                    ELSE neutrophils_abs
                END AS DECIMAL(38, 10)
            ),
            4
        ) AS DECIMAL(38, 4)
    ) AS neutrophils_abs,
    CAST(basophils AS DOUBLE) AS basophils,
    CAST(eosinophils AS DOUBLE) AS eosinophils,
    CAST(lymphocytes AS DOUBLE) AS lymphocytes,
    CAST(monocytes AS DOUBLE) AS monocytes,
    CAST(neutrophils AS DOUBLE) AS neutrophils,
    CAST(atypical_lymphocytes AS DOUBLE) AS atypical_lymphocytes,
    CAST(bands AS DOUBLE) AS bands,
    CAST(immature_granulocytes AS DOUBLE) AS immature_granulocytes,
    CAST(metamyelocytes AS DOUBLE) AS metamyelocytes,
    CAST(nrbc AS DOUBLE) AS nrbc
FROM blood_diff
;
