WITH lab_rows AS (
    SELECT
        CAST(p.subject_id_str AS INTEGER) AS subject_id,
        CAST(e.hadm_id_str AS INTEGER) AS hadm_id,
        TRY_CAST(
            COALESCE(l.effective_datetime, l.effective_period_start)
            AS TIMESTAMP_NTZ
        ) AS charttime,
        CAST(s.specimen_id_str AS INTEGER) AS specimen_id,
        p.patient_key,
        e.encounter_key,
        l.code,
        l.system,
        l.value_string,
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
            '52033', '50801', '50802', '50803', '50804', '50805', '50806',
            '50807', '50808', '50809', '50810', '50811', '50813', '50814',
            '50815', '50816', '50817', '50818', '50819', '50820', '50821',
            '50822', '50823', '50824', '50825'
        )
),
bg AS (
    SELECT
        MAX(subject_id) AS subject_id,
        MAX(hadm_id) AS hadm_id,
        MAX(charttime) AS charttime,
        specimen_id,
        MAX(patient_key) AS patient_key,
        MAX(encounter_key) AS encounter_key,
        MAX(CASE WHEN code = '52033' THEN NULLIF(value_string, '___') ELSE NULL END) AS specimen,
        MAX(CASE WHEN code = '50801' THEN quantity_value ELSE NULL END) AS aado2,
        MAX(CASE WHEN code = '50802' THEN quantity_value ELSE NULL END) AS baseexcess,
        MAX(CASE WHEN code = '50803' THEN quantity_value ELSE NULL END) AS bicarbonate,
        MAX(CASE WHEN code = '50804' THEN quantity_value ELSE NULL END) AS totalco2,
        MAX(CASE WHEN code = '50805' THEN quantity_value ELSE NULL END) AS carboxyhemoglobin,
        MAX(CASE WHEN code = '50806' THEN quantity_value ELSE NULL END) AS chloride,
        MAX(CASE WHEN code = '50808' THEN quantity_value ELSE NULL END) AS calcium,
        MAX(
            CASE
                WHEN code = '50809' AND quantity_value <= 10000 THEN quantity_value
                ELSE NULL
            END
        ) AS glucose,
        MAX(
            CASE
                WHEN code = '50810' AND quantity_value <= 100 THEN quantity_value
                ELSE NULL
            END
        ) AS hematocrit,
        MAX(CASE WHEN code = '50811' THEN quantity_value ELSE NULL END) AS hemoglobin,
        MAX(
            CASE
                WHEN code = '50813' AND quantity_value <= 10000 THEN quantity_value
                ELSE NULL
            END
        ) AS lactate,
        MAX(CASE WHEN code = '50814' THEN quantity_value ELSE NULL END) AS methemoglobin,
        MAX(
            CASE
                WHEN code = '50816' THEN
                    CASE
                        WHEN quantity_value > 20 AND quantity_value <= 100 THEN quantity_value
                        WHEN quantity_value > 0.2 AND quantity_value <= 1.0 THEN quantity_value * 100.0
                        ELSE NULL
                    END
                ELSE NULL
            END
        ) AS fio2,
        MAX(
            CASE
                WHEN code = '50817' AND quantity_value <= 100 THEN quantity_value
                ELSE NULL
            END
        ) AS so2,
        MAX(CASE WHEN code = '50818' THEN quantity_value ELSE NULL END) AS pco2,
        MAX(CASE WHEN code = '50820' THEN quantity_value ELSE NULL END) AS ph,
        MAX(CASE WHEN code = '50821' THEN quantity_value ELSE NULL END) AS po2,
        MAX(CASE WHEN code = '50822' THEN quantity_value ELSE NULL END) AS potassium,
        MAX(CASE WHEN code = '50824' THEN quantity_value ELSE NULL END) AS sodium,
        MAX(CASE WHEN code = '50825' THEN quantity_value ELSE NULL END) AS temperature
    FROM lab_rows
    GROUP BY specimen_id
),
chart_rows AS (
    SELECT
        CAST(p.subject_id_str AS INTEGER) AS subject_id,
        TRY_CAST(
            COALESCE(c.effective_datetime, c.effective_period_start)
            AS TIMESTAMP_NTZ
        ) AS charttime,
        c.code,
        CAST(c.quantity_value AS DOUBLE) AS quantity_value
    FROM chart_observation c
    INNER JOIN patient p
        ON c.patient_key = p.patient_key
    WHERE c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND c.code IN ('220277', '223835')
),
stg_spo2 AS (
    SELECT
        subject_id,
        charttime,
        AVG(quantity_value) AS spo2
    FROM chart_rows
    WHERE code = '220277'
        AND quantity_value > 0
        AND quantity_value <= 100
    GROUP BY subject_id, charttime
),
stg_fio2 AS (
    SELECT
        subject_id,
        charttime,
        CAST(
            MAX(
                CASE
                    WHEN code = '223835' AND quantity_value > 0.2 AND quantity_value <= 1
                        THEN quantity_value * 100
                    WHEN code = '223835' AND quantity_value > 1 AND quantity_value < 20
                        THEN NULL
                    WHEN code = '223835' AND quantity_value >= 20 AND quantity_value <= 100
                        THEN quantity_value
                    ELSE NULL
                END
            ) AS FLOAT
        ) AS fio2_chartevents
    FROM chart_rows
    WHERE code = '223835'
        AND quantity_value > 0
        AND quantity_value <= 100
    GROUP BY subject_id, charttime
),
stg2 AS (
    SELECT
        bg.*,
        ROW_NUMBER() OVER (
            PARTITION BY bg.specimen_id
            ORDER BY s1.charttime DESC
        ) AS lastrowspo2,
        s1.spo2
    FROM bg
    LEFT JOIN stg_spo2 s1
        ON bg.subject_id = s1.subject_id
        AND s1.charttime BETWEEN bg.charttime - INTERVAL 2 HOURS AND bg.charttime
    WHERE bg.po2 IS NOT NULL
),
stg3 AS (
    SELECT
        bg.*,
        ROW_NUMBER() OVER (
            PARTITION BY bg.specimen_id
            ORDER BY s2.charttime DESC
        ) AS lastrowfio2,
        s2.fio2_chartevents
    FROM stg2 bg
    LEFT JOIN stg_fio2 s2
        ON bg.subject_id = s2.subject_id
        AND s2.charttime >= bg.charttime - INTERVAL 4 HOURS
        AND s2.charttime <= bg.charttime
        AND s2.fio2_chartevents > 0
    WHERE bg.lastrowspo2 = 1
),
derived AS (
    SELECT
        subject_id,
        hadm_id,
        patient_key,
        encounter_key,
        charttime,
        specimen,
        so2,
        po2,
        pco2,
        fio2_chartevents,
        fio2,
        aado2,
        CASE
            WHEN po2 IS NULL OR pco2 IS NULL THEN NULL
            WHEN fio2 IS NOT NULL
                THEN (fio2 / 100.0) * (760.0 - 47.0) - (pco2 / 0.8) - po2
            WHEN fio2_chartevents IS NOT NULL
                THEN (fio2_chartevents / 100.0) * (760.0 - 47.0) - (pco2 / 0.8) - po2
            ELSE NULL
        END AS aado2_calc_unrounded,
        CASE
            WHEN po2 IS NULL THEN NULL
            WHEN fio2 IS NOT NULL THEN 100.0 * po2 / fio2
            WHEN fio2_chartevents IS NOT NULL THEN 100.0 * po2 / fio2_chartevents
            ELSE NULL
        END AS pao2fio2ratio,
        ph,
        baseexcess,
        bicarbonate,
        totalco2,
        hematocrit,
        hemoglobin,
        carboxyhemoglobin,
        methemoglobin,
        chloride,
        calcium,
        temperature,
        potassium,
        sodium,
        lactate,
        glucose
    FROM stg3
    WHERE lastrowfio2 = 1
)
SELECT
    CAST(subject_id AS INTEGER) AS subject_id,
    CAST(hadm_id AS INTEGER) AS hadm_id,
    CAST(charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(specimen AS VARCHAR(255)) AS specimen,
    CAST(so2 AS DOUBLE) AS so2,
    CAST(po2 AS DOUBLE) AS po2,
    CAST(pco2 AS DOUBLE) AS pco2,
    CAST(fio2_chartevents AS FLOAT) AS fio2_chartevents,
    CAST(fio2 AS DOUBLE) AS fio2,
    CAST(aado2 AS DOUBLE) AS aado2,
    CAST(ROUND(CAST(aado2_calc_unrounded AS DECIMAL(38, 10)), 4) AS DECIMAL(38, 4)) AS aado2_calc,
    CAST(pao2fio2ratio AS DOUBLE) AS pao2fio2ratio,
    CAST(ph AS DOUBLE) AS ph,
    CAST(baseexcess AS DOUBLE) AS baseexcess,
    CAST(bicarbonate AS DOUBLE) AS bicarbonate,
    CAST(totalco2 AS DOUBLE) AS totalco2,
    CAST(hematocrit AS DOUBLE) AS hematocrit,
    CAST(hemoglobin AS DOUBLE) AS hemoglobin,
    CAST(carboxyhemoglobin AS DOUBLE) AS carboxyhemoglobin,
    CAST(methemoglobin AS DOUBLE) AS methemoglobin,
    CAST(chloride AS DOUBLE) AS chloride,
    CAST(calcium AS DOUBLE) AS calcium,
    CAST(temperature AS DOUBLE) AS temperature,
    CAST(potassium AS DOUBLE) AS potassium,
    CAST(sodium AS DOUBLE) AS sodium,
    CAST(lactate AS DOUBLE) AS lactate,
    CAST(glucose AS DOUBLE) AS glucose,
    patient_key,
    encounter_key
FROM derived
;
