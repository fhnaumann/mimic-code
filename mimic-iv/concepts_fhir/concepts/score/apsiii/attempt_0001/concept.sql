WITH icu AS (
    SELECT
        i.icu_encounter_key,
        i.patient_key,
        i.encounter_key,
        i.stay_id_str,
        TRY_CAST(i.intime_datetime AS TIMESTAMP_NTZ) AS intime,
        TRY_CAST(i.outtime_datetime AS TIMESTAMP_NTZ) AS outtime
    FROM icu_encounter AS i
    WHERE i.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
        AND i.stay_id_str IS NOT NULL
), pa AS (
    SELECT
        ie.icu_encounter_key,
        bg.charttime,
        bg.po2 AS pao2,
        ROW_NUMBER() OVER (
            PARTITION BY ie.icu_encounter_key
            ORDER BY bg.po2 DESC
        ) AS rn
    FROM bg AS bg
    INNER JOIN icu AS ie
        ON bg.encounter_key = ie.encounter_key
        AND bg.charttime >= ie.intime
        AND bg.charttime < ie.outtime
    LEFT JOIN ventilation AS vd
        ON ie.icu_encounter_key = vd.icu_encounter_key
        AND bg.charttime >= vd.starttime
        AND bg.charttime <= vd.endtime
        AND vd.ventilation_status = 'InvasiveVent'
    WHERE vd.icu_encounter_key IS NULL
        AND COALESCE(bg.fio2, bg.fio2_chartevents, 21) < 50
        AND bg.po2 IS NOT NULL
        AND bg.specimen = 'ART.'
), aa AS (
    SELECT
        ie.icu_encounter_key,
        bg.charttime,
        bg.aado2,
        ROW_NUMBER() OVER (
            PARTITION BY ie.icu_encounter_key
            ORDER BY bg.aado2 DESC
        ) AS rn
    FROM bg AS bg
    INNER JOIN icu AS ie
        ON bg.encounter_key = ie.encounter_key
        AND bg.charttime >= ie.intime
        AND bg.charttime < ie.outtime
    INNER JOIN ventilation AS vd
        ON ie.icu_encounter_key = vd.icu_encounter_key
        AND bg.charttime >= vd.starttime
        AND bg.charttime <= vd.endtime
        AND vd.ventilation_status = 'InvasiveVent'
    WHERE vd.icu_encounter_key IS NOT NULL
        AND COALESCE(bg.fio2, bg.fio2_chartevents) >= 50
        AND bg.aado2 IS NOT NULL
        AND bg.specimen = 'ART.'
), acidbase AS (
    SELECT
        ie.icu_encounter_key,
        bg.ph,
        bg.pco2 AS paco2,
        CASE
            WHEN bg.ph IS NULL OR bg.pco2 IS NULL THEN NULL
            WHEN bg.ph < 7.20 THEN
                CASE
                    WHEN bg.pco2 < 50 THEN 12
                    ELSE 4
                END
            WHEN bg.ph < 7.30 THEN
                CASE
                    WHEN bg.pco2 < 30 THEN 9
                    WHEN bg.pco2 < 40 THEN 6
                    WHEN bg.pco2 < 50 THEN 3
                    ELSE 2
                END
            WHEN bg.ph < 7.35 THEN
                CASE
                    WHEN bg.pco2 < 30 THEN 9
                    WHEN bg.pco2 < 45 THEN 0
                    ELSE 1
                END
            WHEN bg.ph < 7.45 THEN
                CASE
                    WHEN bg.pco2 < 30 THEN 5
                    WHEN bg.pco2 < 45 THEN 0
                    ELSE 1
                END
            WHEN bg.ph < 7.50 THEN
                CASE
                    WHEN bg.pco2 < 30 THEN 5
                    WHEN bg.pco2 < 35 THEN 0
                    WHEN bg.pco2 < 45 THEN 2
                    ELSE 12
                END
            WHEN bg.ph < 7.60 THEN
                CASE
                    WHEN bg.pco2 < 40 THEN 3
                    ELSE 12
                END
            ELSE
                CASE
                    WHEN bg.pco2 < 25 THEN 0
                    WHEN bg.pco2 < 40 THEN 3
                    ELSE 12
                END
        END AS acidbase_score
    FROM bg AS bg
    INNER JOIN icu AS ie
        ON bg.encounter_key = ie.encounter_key
        AND bg.charttime >= ie.intime
        AND bg.charttime < ie.outtime
    WHERE bg.ph IS NOT NULL
        AND bg.pco2 IS NOT NULL
        AND bg.specimen = 'ART.'
), acidbase_max AS (
    SELECT
        icu_encounter_key,
        acidbase_score,
        ph,
        paco2,
        ROW_NUMBER() OVER (
            PARTITION BY icu_encounter_key
            ORDER BY acidbase_score DESC
        ) AS acidbase_rn
    FROM acidbase
), icd AS (
    SELECT
        c.encounter_key,
        MAX(
            CASE
                WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9'
                    AND SUBSTR(c.code, 1, 4) IN ('5854', '5855', '5856') THEN 1
                WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
                    AND SUBSTR(c.code, 1, 4) IN ('N184', 'N185', 'N186') THEN 1
                ELSE 0
            END
        ) AS ckd
    FROM condition AS c
    INNER JOIN hospital_encounter AS h
        ON c.encounter_key = h.encounter_key
    WHERE h.hadm_id_str IS NOT NULL
    GROUP BY c.encounter_key
), arf AS (
    SELECT
        ie.icu_encounter_key,
        CASE
            WHEN labs.creatinine_max >= 1.5
                AND uo.urineoutput < 410
                AND icd.ckd = 0
                THEN 1
            ELSE 0
        END AS arf
    FROM icu AS ie
    LEFT JOIN first_day_urine_output AS uo
        ON ie.icu_encounter_key = uo.icu_encounter_key
    LEFT JOIN first_day_lab AS labs
        ON ie.icu_encounter_key = labs.icu_encounter_key
    LEFT JOIN icd
        ON ie.encounter_key = icd.encounter_key
), vent AS (
    SELECT
        ie.icu_encounter_key,
        MAX(
            CASE
                WHEN v.icu_encounter_key IS NOT NULL THEN 1
                ELSE 0
            END
        ) AS vent
    FROM icu AS ie
    LEFT JOIN ventilation AS v
        ON ie.icu_encounter_key = v.icu_encounter_key
        AND v.ventilation_status = 'InvasiveVent'
        AND (
            (
                v.starttime >= ie.intime
                AND v.starttime <= ie.intime + INTERVAL 1 DAY
            )
            OR (
                v.endtime >= ie.intime
                AND v.endtime <= ie.intime + INTERVAL 1 DAY
            )
            OR (
                v.starttime <= ie.intime
                AND v.endtime >= ie.intime + INTERVAL 1 DAY
            )
        )
    GROUP BY ie.icu_encounter_key
), cohort AS (
    SELECT
        p.subject_id_str,
        h.hadm_id_str,
        i.stay_id_str,
        i.icu_encounter_key,
        i.patient_key,
        i.encounter_key,
        i.intime,
        i.outtime,
        vital.heart_rate_min,
        vital.heart_rate_max,
        vital.mbp_min,
        vital.mbp_max,
        vital.temperature_min,
        vital.temperature_max,
        vital.resp_rate_min,
        vital.resp_rate_max,
        pa.pao2,
        aa.aado2,
        ab.ph,
        ab.paco2,
        ab.acidbase_score,
        labs.hematocrit_min,
        labs.hematocrit_max,
        labs.wbc_min,
        labs.wbc_max,
        labs.creatinine_min,
        labs.creatinine_max,
        labs.bun_min,
        labs.bun_max,
        labs.sodium_min,
        labs.sodium_max,
        labs.albumin_min,
        labs.albumin_max,
        labs.bilirubin_total_min AS bilirubin_min,
        labs.bilirubin_total_max AS bilirubin_max,
        CASE
            WHEN labs.glucose_max IS NULL AND vital.glucose_max IS NULL THEN NULL
            WHEN labs.glucose_max IS NULL
                OR vital.glucose_max > labs.glucose_max
                THEN vital.glucose_max
            WHEN vital.glucose_max IS NULL
                OR labs.glucose_max > vital.glucose_max
                THEN labs.glucose_max
            ELSE labs.glucose_max
        END AS glucose_max,
        CASE
            WHEN labs.glucose_min IS NULL AND vital.glucose_min IS NULL THEN NULL
            WHEN labs.glucose_min IS NULL
                OR vital.glucose_min < labs.glucose_min
                THEN vital.glucose_min
            WHEN vital.glucose_min IS NULL
                OR labs.glucose_min < vital.glucose_min
                THEN labs.glucose_min
            ELSE labs.glucose_min
        END AS glucose_min,
        vent.vent,
        uo.urineoutput,
        gcs.gcs_min AS mingcs,
        gcs.gcs_motor,
        gcs.gcs_verbal,
        gcs.gcs_eyes,
        gcs.gcs_unable,
        arf.arf
    FROM icu AS i
    INNER JOIN hospital_encounter AS h
        ON i.encounter_key = h.encounter_key
        AND h.hadm_id_str IS NOT NULL
    INNER JOIN patient AS p
        ON i.patient_key = p.patient_key
        AND p.subject_id_str IS NOT NULL
    LEFT JOIN pa
        ON i.icu_encounter_key = pa.icu_encounter_key
        AND pa.rn = 1
    LEFT JOIN aa
        ON i.icu_encounter_key = aa.icu_encounter_key
        AND aa.rn = 1
    LEFT JOIN acidbase_max AS ab
        ON i.icu_encounter_key = ab.icu_encounter_key
        AND ab.acidbase_rn = 1
    LEFT JOIN arf
        ON i.icu_encounter_key = arf.icu_encounter_key
    LEFT JOIN vent
        ON i.icu_encounter_key = vent.icu_encounter_key
    LEFT JOIN first_day_gcs AS gcs
        ON i.icu_encounter_key = gcs.icu_encounter_key
    LEFT JOIN first_day_vitalsign AS vital
        ON i.icu_encounter_key = vital.icu_encounter_key
    LEFT JOIN first_day_urine_output AS uo
        ON i.icu_encounter_key = uo.icu_encounter_key
    LEFT JOIN first_day_lab AS labs
        ON i.icu_encounter_key = labs.icu_encounter_key
), score_min AS (
    SELECT
        cohort.icu_encounter_key,
        CASE
            WHEN heart_rate_min IS NULL THEN NULL
            WHEN heart_rate_min < 40 THEN 8
            WHEN heart_rate_min < 50 THEN 5
            WHEN heart_rate_min < 100 THEN 0
            WHEN heart_rate_min < 110 THEN 1
            WHEN heart_rate_min < 120 THEN 5
            WHEN heart_rate_min < 140 THEN 7
            WHEN heart_rate_min < 155 THEN 13
            WHEN heart_rate_min >= 155 THEN 17
        END AS hr_score,
        CASE
            WHEN mbp_min IS NULL THEN NULL
            WHEN mbp_min < 40 THEN 23
            WHEN mbp_min < 60 THEN 15
            WHEN mbp_min < 70 THEN 7
            WHEN mbp_min < 80 THEN 6
            WHEN mbp_min < 100 THEN 0
            WHEN mbp_min < 120 THEN 4
            WHEN mbp_min < 130 THEN 7
            WHEN mbp_min < 140 THEN 9
            WHEN mbp_min >= 140 THEN 10
        END AS mbp_score,
        CASE
            WHEN temperature_min IS NULL THEN NULL
            WHEN temperature_min < 33.0 THEN 20
            WHEN temperature_min < 33.5 THEN 16
            WHEN temperature_min < 34.0 THEN 13
            WHEN temperature_min < 35.0 THEN 8
            WHEN temperature_min < 36.0 THEN 2
            WHEN temperature_min < 40.0 THEN 0
            WHEN temperature_min >= 40.0 THEN 4
        END AS temp_score,
        CASE
            WHEN resp_rate_min IS NULL THEN NULL
            WHEN vent = 1 AND resp_rate_min < 14 THEN 0
            WHEN resp_rate_min < 6 THEN 17
            WHEN resp_rate_min < 12 THEN 8
            WHEN resp_rate_min < 14 THEN 7
            WHEN resp_rate_min < 25 THEN 0
            WHEN resp_rate_min < 35 THEN 6
            WHEN resp_rate_min < 40 THEN 9
            WHEN resp_rate_min < 50 THEN 11
            WHEN resp_rate_min >= 50 THEN 18
        END AS resp_rate_score,
        CASE
            WHEN hematocrit_min IS NULL THEN NULL
            WHEN hematocrit_min < 41.0 THEN 3
            WHEN hematocrit_min < 50.0 THEN 0
            WHEN hematocrit_min >= 50.0 THEN 3
        END AS hematocrit_score,
        CASE
            WHEN wbc_min IS NULL THEN NULL
            WHEN wbc_min < 1.0 THEN 19
            WHEN wbc_min < 3.0 THEN 5
            WHEN wbc_min < 20.0 THEN 0
            WHEN wbc_min < 25.0 THEN 1
            WHEN wbc_min >= 25.0 THEN 5
        END AS wbc_score,
        CASE
            WHEN creatinine_min IS NULL THEN NULL
            WHEN arf = 1 AND creatinine_min < 1.5 THEN 0
            WHEN arf = 1 AND creatinine_min >= 1.5 THEN 10
            WHEN creatinine_min < 0.5 THEN 3
            WHEN creatinine_min < 1.5 THEN 0
            WHEN creatinine_min < 1.95 THEN 4
            WHEN creatinine_min >= 1.95 THEN 7
        END AS creatinine_score,
        CASE
            WHEN bun_min IS NULL THEN NULL
            WHEN bun_min < 17.0 THEN 0
            WHEN bun_min < 20.0 THEN 2
            WHEN bun_min < 40.0 THEN 7
            WHEN bun_min < 80.0 THEN 11
            WHEN bun_min >= 80.0 THEN 12
        END AS bun_score,
        CASE
            WHEN sodium_min IS NULL THEN NULL
            WHEN sodium_min < 120 THEN 3
            WHEN sodium_min < 135 THEN 2
            WHEN sodium_min < 155 THEN 0
            WHEN sodium_min >= 155 THEN 4
        END AS sodium_score,
        CASE
            WHEN albumin_min IS NULL THEN NULL
            WHEN albumin_min < 2.0 THEN 11
            WHEN albumin_min < 2.5 THEN 6
            WHEN albumin_min < 4.5 THEN 0
            WHEN albumin_min >= 4.5 THEN 4
        END AS albumin_score,
        CASE
            WHEN bilirubin_min IS NULL THEN NULL
            WHEN bilirubin_min < 2.0 THEN 0
            WHEN bilirubin_min < 3.0 THEN 5
            WHEN bilirubin_min < 5.0 THEN 6
            WHEN bilirubin_min < 8.0 THEN 8
            WHEN bilirubin_min >= 8.0 THEN 16
        END AS bilirubin_score,
        CASE
            WHEN glucose_min IS NULL THEN NULL
            WHEN glucose_min < 40 THEN 8
            WHEN glucose_min < 60 THEN 9
            WHEN glucose_min < 200 THEN 0
            WHEN glucose_min < 350 THEN 3
            WHEN glucose_min >= 350 THEN 5
        END AS glucose_score
    FROM cohort
), score_max AS (
    SELECT
        cohort.icu_encounter_key,
        CASE
            WHEN heart_rate_max IS NULL THEN NULL
            WHEN heart_rate_max < 40 THEN 8
            WHEN heart_rate_max < 50 THEN 5
            WHEN heart_rate_max < 100 THEN 0
            WHEN heart_rate_max < 110 THEN 1
            WHEN heart_rate_max < 120 THEN 5
            WHEN heart_rate_max < 140 THEN 7
            WHEN heart_rate_max < 155 THEN 13
            WHEN heart_rate_max >= 155 THEN 17
        END AS hr_score,
        CASE
            WHEN mbp_max IS NULL THEN NULL
            WHEN mbp_max < 40 THEN 23
            WHEN mbp_max < 60 THEN 15
            WHEN mbp_max < 70 THEN 7
            WHEN mbp_max < 80 THEN 6
            WHEN mbp_max < 100 THEN 0
            WHEN mbp_max < 120 THEN 4
            WHEN mbp_max < 130 THEN 7
            WHEN mbp_max < 140 THEN 9
            WHEN mbp_max >= 140 THEN 10
        END AS mbp_score,
        CASE
            WHEN temperature_max IS NULL THEN NULL
            WHEN temperature_max < 33.0 THEN 20
            WHEN temperature_max < 33.5 THEN 16
            WHEN temperature_max < 34.0 THEN 13
            WHEN temperature_max < 35.0 THEN 8
            WHEN temperature_max < 36.0 THEN 2
            WHEN temperature_max < 40.0 THEN 0
            WHEN temperature_max >= 40.0 THEN 4
        END AS temp_score,
        CASE
            WHEN resp_rate_max IS NULL THEN NULL
            WHEN vent = 1 AND resp_rate_max < 14 THEN 0
            WHEN resp_rate_max < 6 THEN 17
            WHEN resp_rate_max < 12 THEN 8
            WHEN resp_rate_max < 14 THEN 7
            WHEN resp_rate_max < 25 THEN 0
            WHEN resp_rate_max < 35 THEN 6
            WHEN resp_rate_max < 40 THEN 9
            WHEN resp_rate_max < 50 THEN 11
            WHEN resp_rate_max >= 50 THEN 18
        END AS resp_rate_score,
        CASE
            WHEN hematocrit_max IS NULL THEN NULL
            WHEN hematocrit_max < 41.0 THEN 3
            WHEN hematocrit_max < 50.0 THEN 0
            WHEN hematocrit_max >= 50.0 THEN 3
        END AS hematocrit_score,
        CASE
            WHEN wbc_max IS NULL THEN NULL
            WHEN wbc_max < 1.0 THEN 19
            WHEN wbc_max < 3.0 THEN 5
            WHEN wbc_max < 20.0 THEN 0
            WHEN wbc_max < 25.0 THEN 1
            WHEN wbc_max >= 25.0 THEN 5
        END AS wbc_score,
        CASE
            WHEN creatinine_max IS NULL THEN NULL
            WHEN arf = 1 AND creatinine_max < 1.5 THEN 0
            WHEN arf = 1 AND creatinine_max >= 1.5 THEN 10
            WHEN creatinine_max < 0.5 THEN 3
            WHEN creatinine_max < 1.5 THEN 0
            WHEN creatinine_max < 1.95 THEN 4
            WHEN creatinine_max >= 1.95 THEN 7
        END AS creatinine_score,
        CASE
            WHEN bun_max IS NULL THEN NULL
            WHEN bun_max < 17.0 THEN 0
            WHEN bun_max < 20.0 THEN 2
            WHEN bun_max < 40.0 THEN 7
            WHEN bun_max < 80.0 THEN 11
            WHEN bun_max >= 80.0 THEN 12
        END AS bun_score,
        CASE
            WHEN sodium_max IS NULL THEN NULL
            WHEN sodium_max < 120 THEN 3
            WHEN sodium_max < 135 THEN 2
            WHEN sodium_max < 155 THEN 0
            WHEN sodium_max >= 155 THEN 4
        END AS sodium_score,
        CASE
            WHEN albumin_max IS NULL THEN NULL
            WHEN albumin_max < 2.0 THEN 11
            WHEN albumin_max < 2.5 THEN 6
            WHEN albumin_max < 4.5 THEN 0
            WHEN albumin_max >= 4.5 THEN 4
        END AS albumin_score,
        CASE
            WHEN bilirubin_max IS NULL THEN NULL
            WHEN bilirubin_max < 2.0 THEN 0
            WHEN bilirubin_max < 3.0 THEN 5
            WHEN bilirubin_max < 5.0 THEN 6
            WHEN bilirubin_max < 8.0 THEN 8
            WHEN bilirubin_max >= 8.0 THEN 16
        END AS bilirubin_score,
        CASE
            WHEN glucose_max IS NULL THEN NULL
            WHEN glucose_max < 40 THEN 8
            WHEN glucose_max < 60 THEN 9
            WHEN glucose_max < 200 THEN 0
            WHEN glucose_max < 350 THEN 3
            WHEN glucose_max >= 350 THEN 5
        END AS glucose_score
    FROM cohort
), scorecomp AS (
    SELECT
        co.*,
        CASE
            WHEN heart_rate_max IS NULL THEN NULL
            WHEN ABS(heart_rate_max - 75) > ABS(heart_rate_min - 75)
                THEN smax.hr_score
            WHEN ABS(heart_rate_max - 75) < ABS(heart_rate_min - 75)
                THEN smin.hr_score
            WHEN ABS(heart_rate_max - 75) = ABS(heart_rate_min - 75)
                AND smax.hr_score >= smin.hr_score
                THEN smax.hr_score
            WHEN ABS(heart_rate_max - 75) = ABS(heart_rate_min - 75)
                AND smax.hr_score < smin.hr_score
                THEN smin.hr_score
        END AS hr_score,
        CASE
            WHEN mbp_max IS NULL THEN NULL
            WHEN ABS(mbp_max - 90) > ABS(mbp_min - 90)
                THEN smax.mbp_score
            WHEN ABS(mbp_max - 90) < ABS(mbp_min - 90)
                THEN smin.mbp_score
            WHEN ABS(mbp_max - 90) = ABS(mbp_min - 90)
                AND smax.mbp_score >= smin.mbp_score
                THEN smax.mbp_score
            WHEN ABS(mbp_max - 90) = ABS(mbp_min - 90)
                AND smax.mbp_score < smin.mbp_score
                THEN smin.mbp_score
        END AS mbp_score,
        CASE
            WHEN temperature_max IS NULL THEN NULL
            WHEN ABS(temperature_max - 38) > ABS(temperature_min - 38)
                THEN smax.temp_score
            WHEN ABS(temperature_max - 38) < ABS(temperature_min - 38)
                THEN smin.temp_score
            WHEN ABS(temperature_max - 38) = ABS(temperature_min - 38)
                AND smax.temp_score >= smin.temp_score
                THEN smax.temp_score
            WHEN ABS(temperature_max - 38) = ABS(temperature_min - 38)
                AND smax.temp_score < smin.temp_score
                THEN smin.temp_score
        END AS temp_score,
        CASE
            WHEN resp_rate_max IS NULL THEN NULL
            WHEN ABS(resp_rate_max - 19) > ABS(resp_rate_min - 19)
                THEN smax.resp_rate_score
            WHEN ABS(resp_rate_max - 19) < ABS(resp_rate_min - 19)
                THEN smin.resp_rate_score
            WHEN ABS(resp_rate_max - 19) = ABS(resp_rate_max - 19)
                AND smax.resp_rate_score >= smin.resp_rate_score
                THEN smax.resp_rate_score
            WHEN ABS(resp_rate_max - 19) = ABS(resp_rate_max - 19)
                AND smax.resp_rate_score < smin.resp_rate_score
                THEN smin.resp_rate_score
        END AS resp_rate_score,
        CASE
            WHEN hematocrit_max IS NULL THEN NULL
            WHEN ABS(hematocrit_max - 45.5) > ABS(hematocrit_min - 45.5)
                THEN smax.hematocrit_score
            WHEN ABS(hematocrit_max - 45.5) < ABS(hematocrit_min - 45.5)
                THEN smin.hematocrit_score
            WHEN ABS(hematocrit_max - 45.5) = ABS(hematocrit_max - 45.5)
                AND smax.hematocrit_score >= smin.hematocrit_score
                THEN smax.hematocrit_score
            WHEN ABS(hematocrit_max - 45.5) = ABS(hematocrit_max - 45.5)
                AND smax.hematocrit_score < smin.hematocrit_score
                THEN smin.hematocrit_score
        END AS hematocrit_score,
        CASE
            WHEN wbc_max IS NULL THEN NULL
            WHEN ABS(wbc_max - 11.5) > ABS(wbc_min - 11.5)
                THEN smax.wbc_score
            WHEN ABS(wbc_max - 11.5) < ABS(wbc_min - 11.5)
                THEN smin.wbc_score
            WHEN ABS(wbc_max - 11.5) = ABS(wbc_max - 11.5)
                AND smax.wbc_score >= smin.wbc_score
                THEN smax.wbc_score
            WHEN ABS(wbc_max - 11.5) = ABS(wbc_max - 11.5)
                AND smax.wbc_score < smin.wbc_score
                THEN smin.wbc_score
        END AS wbc_score,
        CASE
            WHEN creatinine_max IS NULL THEN NULL
            WHEN arf = 1 THEN smax.creatinine_score
            WHEN ABS(creatinine_max - 1) > ABS(creatinine_min - 1)
                THEN smax.creatinine_score
            WHEN ABS(creatinine_max - 1) < ABS(creatinine_min - 1)
                THEN smin.creatinine_score
            WHEN smax.creatinine_score >= smin.creatinine_score
                THEN smax.creatinine_score
            WHEN smax.creatinine_score < smin.creatinine_score
                THEN smin.creatinine_score
        END AS creatinine_score,
        CASE
            WHEN bun_max IS NULL THEN NULL
            ELSE smax.bun_score
        END AS bun_score,
        CASE
            WHEN sodium_max IS NULL THEN NULL
            WHEN ABS(sodium_max - 145.5) > ABS(sodium_min - 145.5)
                THEN smax.sodium_score
            WHEN ABS(sodium_max - 145.5) < ABS(sodium_min - 145.5)
                THEN smin.sodium_score
            WHEN ABS(sodium_max - 145.5) = ABS(sodium_max - 145.5)
                AND smax.sodium_score >= smin.sodium_score
                THEN smax.sodium_score
            WHEN ABS(sodium_max - 145.5) = ABS(sodium_max - 145.5)
                AND smax.sodium_score < smin.sodium_score
                THEN smin.sodium_score
        END AS sodium_score,
        CASE
            WHEN albumin_max IS NULL THEN NULL
            WHEN ABS(albumin_max - 3.5) > ABS(albumin_min - 3.5)
                THEN smax.albumin_score
            WHEN ABS(albumin_max - 3.5) < ABS(albumin_min - 3.5)
                THEN smin.albumin_score
            WHEN ABS(albumin_max - 3.5) = ABS(albumin_max - 3.5)
                AND smax.albumin_score >= smin.albumin_score
                THEN smax.albumin_score
            WHEN ABS(albumin_max - 3.5) = ABS(albumin_max - 3.5)
                AND smax.albumin_score < smin.albumin_score
                THEN smin.albumin_score
        END AS albumin_score,
        CASE
            WHEN bilirubin_max IS NULL THEN NULL
            ELSE smax.bilirubin_score
        END AS bilirubin_score,
        CASE
            WHEN glucose_max IS NULL THEN NULL
            WHEN ABS(glucose_max - 130) > ABS(glucose_min - 130)
                THEN smax.glucose_score
            WHEN ABS(glucose_max - 130) < ABS(glucose_min - 130)
                THEN smin.glucose_score
            WHEN ABS(glucose_max - 130) = ABS(glucose_max - 130)
                AND smax.glucose_score >= smin.glucose_score
                THEN smax.glucose_score
            WHEN ABS(glucose_max - 130) = ABS(glucose_max - 130)
                AND smax.glucose_score < smin.glucose_score
                THEN smin.glucose_score
        END AS glucose_score,
        CASE
            WHEN urineoutput IS NULL THEN NULL
            WHEN urineoutput < 400 THEN 15
            WHEN urineoutput < 600 THEN 8
            WHEN urineoutput < 900 THEN 7
            WHEN urineoutput < 1500 THEN 5
            WHEN urineoutput < 2000 THEN 4
            WHEN urineoutput < 4000 THEN 0
            WHEN urineoutput >= 4000 THEN 1
        END AS uo_score,
        CASE
            WHEN gcs_unable = 1 THEN 0
            WHEN gcs_eyes = 1 THEN
                CASE
                    WHEN gcs_verbal = 1 AND gcs_motor IN (1, 2) THEN 48
                    WHEN gcs_verbal = 1 AND gcs_motor IN (3, 4) THEN 33
                    WHEN gcs_verbal = 1 AND gcs_motor IN (5, 6) THEN 16
                    WHEN gcs_verbal IN (2, 3) AND gcs_motor IN (1, 2) THEN 29
                    WHEN gcs_verbal IN (2, 3) AND gcs_motor IN (3, 4) THEN 24
                    WHEN gcs_verbal IN (2, 3) AND gcs_motor >= 5 THEN NULL
                    WHEN gcs_verbal >= 4 THEN NULL
                END
            WHEN gcs_eyes > 1 THEN
                CASE
                    WHEN gcs_verbal = 1 AND gcs_motor IN (1, 2) THEN 29
                    WHEN gcs_verbal = 1 AND gcs_motor IN (3, 4) THEN 24
                    WHEN gcs_verbal = 1 AND gcs_motor IN (5, 6) THEN 15
                    WHEN gcs_verbal IN (2, 3) AND gcs_motor IN (1, 2) THEN 29
                    WHEN gcs_verbal IN (2, 3) AND gcs_motor IN (3, 4) THEN 24
                    WHEN gcs_verbal IN (2, 3) AND gcs_motor = 5 THEN 13
                    WHEN gcs_verbal IN (2, 3) AND gcs_motor = 6 THEN 10
                    WHEN gcs_verbal = 4 AND gcs_motor IN (1, 2, 3, 4) THEN 13
                    WHEN gcs_verbal = 4 AND gcs_motor = 5 THEN 8
                    WHEN gcs_verbal = 4 AND gcs_motor = 6 THEN 3
                    WHEN gcs_verbal = 5 AND gcs_motor IN (1, 2, 3, 4, 5) THEN 3
                    WHEN gcs_verbal = 5 AND gcs_motor = 6 THEN 0
                END
            ELSE NULL
        END AS gcs_score,
        CASE
            WHEN pao2 IS NULL AND aado2 IS NULL THEN NULL
            WHEN pao2 IS NOT NULL THEN
                CASE
                    WHEN pao2 < 50 THEN 15
                    WHEN pao2 < 70 THEN 5
                    WHEN pao2 < 80 THEN 2
                    ELSE 0
                END
            WHEN aado2 IS NOT NULL THEN
                CASE
                    WHEN aado2 < 100 THEN 0
                    WHEN aado2 < 250 THEN 7
                    WHEN aado2 < 350 THEN 9
                    WHEN aado2 < 500 THEN 11
                    WHEN aado2 >= 500 THEN 14
                    ELSE 0
                END
        END AS pao2_aado2_score
    FROM cohort AS co
    LEFT JOIN score_min AS smin
        ON co.icu_encounter_key = smin.icu_encounter_key
    LEFT JOIN score_max AS smax
        ON co.icu_encounter_key = smax.icu_encounter_key
), score AS (
    SELECT
        s.*,
        COALESCE(hr_score, 0)
            + COALESCE(mbp_score, 0)
            + COALESCE(temp_score, 0)
            + COALESCE(resp_rate_score, 0)
            + COALESCE(pao2_aado2_score, 0)
            + COALESCE(hematocrit_score, 0)
            + COALESCE(wbc_score, 0)
            + COALESCE(creatinine_score, 0)
            + COALESCE(uo_score, 0)
            + COALESCE(bun_score, 0)
            + COALESCE(sodium_score, 0)
            + COALESCE(albumin_score, 0)
            + COALESCE(bilirubin_score, 0)
            + COALESCE(glucose_score, 0)
            + COALESCE(acidbase_score, 0)
            + COALESCE(gcs_score, 0) AS apsiii
    FROM scorecomp AS s
), final_rows AS (
    SELECT
        p.subject_id_str,
        h.hadm_id_str,
        i.stay_id_str,
        s.apsiii,
        1 / (1 + EXP(-(-4.4360 + 0.04726 * s.apsiii))) AS apsiii_prob,
        s.hr_score,
        s.mbp_score,
        s.temp_score,
        s.resp_rate_score,
        s.pao2_aado2_score,
        s.hematocrit_score,
        s.wbc_score,
        s.creatinine_score,
        s.uo_score,
        s.bun_score,
        s.sodium_score,
        s.albumin_score,
        s.bilirubin_score,
        s.glucose_score,
        s.acidbase_score,
        s.gcs_score,
        h.encounter_key,
        i.icu_encounter_key,
        p.patient_key
    FROM icu AS i
    LEFT JOIN score AS s
        ON i.icu_encounter_key = s.icu_encounter_key
    LEFT JOIN hospital_encounter AS h
        ON i.encounter_key = h.encounter_key
    LEFT JOIN patient AS p
        ON i.patient_key = p.patient_key
)
SELECT
    CAST(f.subject_id_str AS INTEGER) AS subject_id,
    CAST(f.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(f.stay_id_str AS INTEGER) AS stay_id,
    CAST(f.apsiii AS INTEGER) AS apsiii,
    CAST(f.apsiii_prob AS DOUBLE) AS apsiii_prob,
    CAST(f.hr_score AS INTEGER) AS hr_score,
    CAST(f.mbp_score AS INTEGER) AS mbp_score,
    CAST(f.temp_score AS INTEGER) AS temp_score,
    CAST(f.resp_rate_score AS INTEGER) AS resp_rate_score,
    CAST(f.pao2_aado2_score AS INTEGER) AS pao2_aado2_score,
    CAST(f.hematocrit_score AS INTEGER) AS hematocrit_score,
    CAST(f.wbc_score AS INTEGER) AS wbc_score,
    CAST(f.creatinine_score AS INTEGER) AS creatinine_score,
    CAST(f.uo_score AS INTEGER) AS uo_score,
    CAST(f.bun_score AS INTEGER) AS bun_score,
    CAST(f.sodium_score AS INTEGER) AS sodium_score,
    CAST(f.albumin_score AS INTEGER) AS albumin_score,
    CAST(f.bilirubin_score AS INTEGER) AS bilirubin_score,
    CAST(f.glucose_score AS INTEGER) AS glucose_score,
    CAST(f.acidbase_score AS INTEGER) AS acidbase_score,
    CAST(f.gcs_score AS INTEGER) AS gcs_score,
    f.encounter_key AS encounter_key,
    f.icu_encounter_key AS icu_encounter_key,
    f.patient_key AS patient_key
FROM final_rows AS f
;
