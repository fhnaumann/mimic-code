WITH icu AS (
    SELECT
        i.icu_encounter_key,
        i.patient_key,
        i.encounter_key,
        i.stay_id_str,
        TRY_CAST(i.intime_datetime AS TIMESTAMP_NTZ) AS starttime,
        TRY_CAST(i.intime_datetime AS TIMESTAMP_NTZ) + INTERVAL 24 HOURS AS endtime
    FROM icu_encounter AS i
    WHERE i.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
        AND i.stay_id_str IS NOT NULL
), cpap_events AS (
    SELECT
        c.patient_key,
        c.icu_encounter_key,
        TRY_CAST(c.effective_datetime AS TIMESTAMP_NTZ) AS charttime,
        c.value_string
    FROM cpap_observation AS c
    WHERE c.item_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
        AND c.item_code = '226732'
), cpap AS (
    SELECT
        co.patient_key,
        co.icu_encounter_key,
        GREATEST(
            MIN(ce.charttime - INTERVAL 1 HOUR), co.starttime
        ) AS starttime,
        LEAST(
            MAX(ce.charttime + INTERVAL 4 HOURS), co.endtime
        ) AS endtime,
        MAX(
            CASE
                WHEN LOWER(ce.value_string) RLIKE '(cpap mask|bipap)' THEN 1
                ELSE 0
            END
        ) AS cpap
    FROM icu AS co
    INNER JOIN cpap_events AS ce
        ON co.icu_encounter_key = ce.icu_encounter_key
            AND ce.charttime > co.starttime
            AND ce.charttime <= co.endtime
    WHERE LOWER(ce.value_string) RLIKE '(cpap mask|bipap)'
    GROUP BY co.patient_key, co.icu_encounter_key, co.starttime, co.endtime
), surgflag AS (
    SELECT
        h.encounter_key,
        CASE
            WHEN LOWER(h.service_code) LIKE '%surg%' THEN 1 ELSE 0
        END AS surgical,
        1 AS serviceorder
    FROM hospital_encounter AS h
    WHERE h.hadm_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp'
        AND h.hadm_id_str IS NOT NULL
), comorb AS (
    SELECT
        c.encounter_key,
        MAX(CASE
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9'
                AND SUBSTR(c.code, 1, 3) BETWEEN '042' AND '044' THEN 1
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
                AND SUBSTR(c.code, 1, 3) BETWEEN 'B20' AND 'B22' THEN 1
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
                AND SUBSTR(c.code, 1, 3) = 'B24' THEN 1
            ELSE 0
        END) AS aids,
        MAX(CASE
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9' THEN
                CASE
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20000' AND '20238' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20240' AND '20248' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20250' AND '20302' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20310' AND '20312' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20302' AND '20382' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20400' AND '20522' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20580' AND '20702' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20720' AND '20892' THEN 1
                    WHEN SUBSTR(c.code, 1, 4) IN ('2386', '2733') THEN 1
                    ELSE 0
                END
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
                AND SUBSTR(c.code, 1, 3) BETWEEN 'C81' AND 'C96' THEN 1
            ELSE 0
        END) AS hem,
        MAX(CASE
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9' THEN
                CASE
                    WHEN SUBSTR(c.code, 1, 4) BETWEEN '1960' AND '1991' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) BETWEEN '20970' AND '20975' THEN 1
                    WHEN SUBSTR(c.code, 1, 5) IN ('20979', '78951') THEN 1
                    ELSE 0
                END
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
                AND SUBSTR(c.code, 1, 3) BETWEEN 'C77' AND 'C79' THEN 1
            WHEN c.system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10'
                AND SUBSTR(c.code, 1, 4) = 'C800' THEN 1
            ELSE 0
        END) AS mets
    FROM condition AS c
    INNER JOIN hospital_encounter AS h
        ON c.encounter_key = h.encounter_key
    WHERE h.hadm_id_str IS NOT NULL
    GROUP BY c.encounter_key
), pafi1 AS (
    SELECT
        co.icu_encounter_key,
        bg.charttime,
        bg.pao2fio2ratio AS pao2fio2,
        CASE WHEN vd.icu_encounter_key IS NOT NULL THEN 1 ELSE 0 END AS vent,
        CASE WHEN cp.patient_key IS NOT NULL THEN 1 ELSE 0 END AS cpap
    FROM icu AS co
    LEFT JOIN bg AS bg
        ON co.patient_key = bg.patient_key
            AND bg.specimen = 'ART.'
            AND bg.charttime > co.starttime
            AND bg.charttime <= co.endtime
    LEFT JOIN ventilation AS vd
        ON co.icu_encounter_key = vd.icu_encounter_key
            AND bg.charttime > vd.starttime
            AND bg.charttime <= vd.endtime
            AND vd.ventilation_status = 'InvasiveVent'
    LEFT JOIN cpap AS cp
        ON bg.patient_key = cp.patient_key
            AND bg.charttime > cp.starttime
            AND bg.charttime <= cp.endtime
), pafi2 AS (
    SELECT
        icu_encounter_key,
        MIN(pao2fio2) AS pao2fio2_vent_min
    FROM pafi1
    WHERE vent = 1 OR cpap = 1
    GROUP BY icu_encounter_key
), gcs_agg AS (
    SELECT
        co.icu_encounter_key,
        MIN(g.gcs) AS mingcs
    FROM icu AS co
    LEFT JOIN gcs AS g
        ON co.icu_encounter_key = g.icu_encounter_key
            AND co.starttime < g.charttime
            AND g.charttime <= co.endtime
    GROUP BY co.icu_encounter_key
), vital AS (
    SELECT
        co.icu_encounter_key,
        MIN(v.heart_rate) AS heartrate_min,
        MAX(v.heart_rate) AS heartrate_max,
        MIN(v.sbp) AS sysbp_min,
        MAX(v.sbp) AS sysbp_max,
        MIN(v.temperature) AS tempc_min,
        MAX(v.temperature) AS tempc_max
    FROM icu AS co
    LEFT JOIN vitalsign AS v
        ON co.patient_key = v.patient_key
            AND co.starttime < v.charttime
            AND co.endtime >= v.charttime
    GROUP BY co.icu_encounter_key
), uo AS (
    SELECT
        co.icu_encounter_key,
        SUM(u.urineoutput) AS urineoutput
    FROM icu AS co
    LEFT JOIN urine_output AS u
        ON co.icu_encounter_key = u.icu_encounter_key
            AND co.starttime < u.charttime
            AND co.endtime >= u.charttime
    GROUP BY co.icu_encounter_key
), labs AS (
    SELECT
        co.icu_encounter_key,
        MIN(l.bun) AS bun_min,
        MAX(l.bun) AS bun_max,
        MIN(l.potassium) AS potassium_min,
        MAX(l.potassium) AS potassium_max,
        MIN(l.sodium) AS sodium_min,
        MAX(l.sodium) AS sodium_max,
        MIN(l.bicarbonate) AS bicarbonate_min,
        MAX(l.bicarbonate) AS bicarbonate_max
    FROM icu AS co
    LEFT JOIN chemistry AS l
        ON co.patient_key = l.patient_key
            AND co.starttime < l.charttime
            AND co.endtime >= l.charttime
    GROUP BY co.icu_encounter_key
), cbc AS (
    SELECT
        co.icu_encounter_key,
        MIN(c.wbc) AS wbc_min,
        MAX(c.wbc) AS wbc_max
    FROM icu AS co
    LEFT JOIN complete_blood_count AS c
        ON co.patient_key = c.patient_key
            AND co.starttime < c.charttime
            AND co.endtime >= c.charttime
    GROUP BY co.icu_encounter_key
), enz AS (
    SELECT
        co.icu_encounter_key,
        MIN(e.bilirubin_total) AS bilirubin_min,
        MAX(e.bilirubin_total) AS bilirubin_max
    FROM icu AS co
    LEFT JOIN enzyme AS e
        ON co.patient_key = e.patient_key
            AND co.starttime < e.charttime
            AND co.endtime >= e.charttime
    GROUP BY co.icu_encounter_key
), cohort AS (
    SELECT
        p.subject_id_str,
        h.hadm_id_str,
        i.stay_id_str,
        i.patient_key,
        i.encounter_key,
        i.icu_encounter_key,
        i.starttime,
        i.endtime,
        va.age,
        vital.heartrate_max,
        vital.heartrate_min,
        vital.sysbp_max,
        vital.sysbp_min,
        vital.tempc_max,
        vital.tempc_min,
        pf.pao2fio2_vent_min,
        uo.urineoutput,
        labs.bun_min,
        labs.bun_max,
        cbc.wbc_min,
        cbc.wbc_max,
        labs.potassium_min,
        labs.potassium_max,
        labs.sodium_min,
        labs.sodium_max,
        labs.bicarbonate_min,
        labs.bicarbonate_max,
        enz.bilirubin_min,
        enz.bilirubin_max,
        gcs.mingcs,
        comorb.aids,
        comorb.hem,
        comorb.mets,
        CASE
            WHEN h.admission_priority_code = 'EL' AND sf.surgical = 1
                THEN 'ScheduledSurgical'
            WHEN h.admission_priority_code <> 'EL' AND sf.surgical = 1
                THEN 'UnscheduledSurgical'
            ELSE 'Medical'
        END AS admissiontype
    FROM icu AS i
    INNER JOIN hospital_encounter AS h
        ON i.encounter_key = h.encounter_key
            AND h.hadm_id_str IS NOT NULL
    INNER JOIN patient AS p
        ON i.patient_key = p.patient_key
            AND p.subject_id_str IS NOT NULL
    LEFT JOIN age AS va
        ON i.encounter_key = va.encounter_key
    LEFT JOIN pafi2 AS pf
        ON i.icu_encounter_key = pf.icu_encounter_key
    LEFT JOIN surgflag AS sf
        ON i.encounter_key = sf.encounter_key
            AND sf.serviceorder = 1
    LEFT JOIN comorb
        ON i.encounter_key = comorb.encounter_key
    LEFT JOIN gcs_agg AS gcs
        ON i.icu_encounter_key = gcs.icu_encounter_key
    LEFT JOIN vital
        ON i.icu_encounter_key = vital.icu_encounter_key
    LEFT JOIN uo
        ON i.icu_encounter_key = uo.icu_encounter_key
    LEFT JOIN labs
        ON i.icu_encounter_key = labs.icu_encounter_key
    LEFT JOIN cbc
        ON i.icu_encounter_key = cbc.icu_encounter_key
    LEFT JOIN enz
        ON i.icu_encounter_key = enz.icu_encounter_key
), scorecomp AS (
    SELECT
        cohort.*,
        CASE
            WHEN age IS NULL THEN NULL
            WHEN age < 40 THEN 0
            WHEN age < 60 THEN 7
            WHEN age < 70 THEN 12
            WHEN age < 75 THEN 15
            WHEN age < 80 THEN 16
            WHEN age >= 80 THEN 18
        END AS age_score,
        CASE
            WHEN heartrate_max IS NULL THEN NULL
            WHEN heartrate_min < 40 THEN 11
            WHEN heartrate_max >= 160 THEN 7
            WHEN heartrate_max >= 120 THEN 4
            WHEN heartrate_min < 70 THEN 2
            WHEN heartrate_max >= 70 AND heartrate_max < 120
                AND heartrate_min >= 70 AND heartrate_min < 120 THEN 0
        END AS hr_score,
        CASE
            WHEN sysbp_min IS NULL THEN NULL
            WHEN sysbp_min < 70 THEN 13
            WHEN sysbp_min < 100 THEN 5
            WHEN sysbp_max >= 200 THEN 2
            WHEN sysbp_max >= 100 AND sysbp_max < 200
                AND sysbp_min >= 100 AND sysbp_min < 200 THEN 0
        END AS sysbp_score,
        CASE
            WHEN tempc_max IS NULL THEN NULL
            WHEN tempc_max >= 39.0 THEN 3
            WHEN tempc_min < 39.0 THEN 0
        END AS temp_score,
        CASE
            WHEN pao2fio2_vent_min IS NULL THEN NULL
            WHEN pao2fio2_vent_min < 100 THEN 11
            WHEN pao2fio2_vent_min < 200 THEN 9
            WHEN pao2fio2_vent_min >= 200 THEN 6
        END AS pao2fio2_score,
        CASE
            WHEN urineoutput IS NULL THEN NULL
            WHEN urineoutput < 500.0 THEN 11
            WHEN urineoutput < 1000.0 THEN 4
            WHEN urineoutput >= 1000.0 THEN 0
        END AS uo_score,
        CASE
            WHEN bun_max IS NULL THEN NULL
            WHEN bun_max < 28.0 THEN 0
            WHEN bun_max < 84.0 THEN 6
            WHEN bun_max >= 84.0 THEN 10
        END AS bun_score,
        CASE
            WHEN wbc_max IS NULL THEN NULL
            WHEN wbc_min < 1.0 THEN 12
            WHEN wbc_max >= 20.0 THEN 3
            WHEN wbc_max >= 1.0 AND wbc_max < 20.0
                AND wbc_min >= 1.0 AND wbc_min < 20.0 THEN 0
        END AS wbc_score,
        CASE
            WHEN potassium_max IS NULL THEN NULL
            WHEN potassium_min < 3.0 THEN 3
            WHEN potassium_max >= 5.0 THEN 3
            WHEN potassium_max >= 3.0 AND potassium_max < 5.0
                AND potassium_min >= 3.0 AND potassium_min < 5.0 THEN 0
        END AS potassium_score,
        CASE
            WHEN sodium_max IS NULL THEN NULL
            WHEN sodium_min < 125 THEN 5
            WHEN sodium_max >= 145 THEN 1
            WHEN sodium_max >= 125 AND sodium_max < 145
                AND sodium_min >= 125 AND sodium_min < 145 THEN 0
        END AS sodium_score,
        CASE
            WHEN bicarbonate_max IS NULL THEN NULL
            WHEN bicarbonate_min < 15.0 THEN 6
            WHEN bicarbonate_min < 20.0 THEN 3
            WHEN bicarbonate_max >= 20.0 AND bicarbonate_min >= 20.0 THEN 0
        END AS bicarbonate_score,
        CASE
            WHEN bilirubin_max IS NULL THEN NULL
            WHEN bilirubin_max < 4.0 THEN 0
            WHEN bilirubin_max < 6.0 THEN 4
            WHEN bilirubin_max >= 6.0 THEN 9
        END AS bilirubin_score,
        CASE
            WHEN mingcs IS NULL THEN NULL
            WHEN mingcs < 3 THEN NULL
            WHEN mingcs < 6 THEN 26
            WHEN mingcs < 9 THEN 13
            WHEN mingcs < 11 THEN 7
            WHEN mingcs < 14 THEN 5
            WHEN mingcs >= 14 AND mingcs <= 15 THEN 0
        END AS gcs_score,
        CASE
            WHEN aids = 1 THEN 17
            WHEN hem = 1 THEN 10
            WHEN mets = 1 THEN 9
            ELSE 0
        END AS comorbidity_score,
        CASE
            WHEN admissiontype = 'ScheduledSurgical' THEN 0
            WHEN admissiontype = 'Medical' THEN 6
            WHEN admissiontype = 'UnscheduledSurgical' THEN 8
            ELSE NULL
        END AS admissiontype_score
    FROM cohort
), score AS (
    SELECT
        s.*,
        COALESCE(age_score, 0)
            + COALESCE(hr_score, 0)
            + COALESCE(sysbp_score, 0)
            + COALESCE(temp_score, 0)
            + COALESCE(pao2fio2_score, 0)
            + COALESCE(uo_score, 0)
            + COALESCE(bun_score, 0)
            + COALESCE(wbc_score, 0)
            + COALESCE(potassium_score, 0)
            + COALESCE(sodium_score, 0)
            + COALESCE(bicarbonate_score, 0)
            + COALESCE(bilirubin_score, 0)
            + COALESCE(gcs_score, 0)
            + COALESCE(comorbidity_score, 0)
            + COALESCE(admissiontype_score, 0) AS sapsii
    FROM scorecomp AS s
), final_rows AS (
    SELECT
        s.subject_id_str,
        s.hadm_id_str,
        s.stay_id_str,
        s.starttime,
        s.endtime,
        s.sapsii,
        1 / (
            1 + EXP(-(-7.7631 + 0.0737 * s.sapsii + 0.9971 * LN(s.sapsii + 1)))
        ) AS sapsii_prob,
        s.age_score,
        s.hr_score,
        s.sysbp_score,
        s.temp_score,
        s.pao2fio2_score,
        s.uo_score,
        s.bun_score,
        s.wbc_score,
        s.potassium_score,
        s.sodium_score,
        s.bicarbonate_score,
        s.bilirubin_score,
        s.gcs_score,
        s.comorbidity_score,
        s.admissiontype_score,
        s.encounter_key,
        s.icu_encounter_key,
        s.patient_key
    FROM score AS s
)
SELECT
    CAST(f.subject_id_str AS INTEGER) AS subject_id,
    CAST(f.hadm_id_str AS INTEGER) AS hadm_id,
    CAST(f.stay_id_str AS INTEGER) AS stay_id,
    CAST(f.starttime AS TIMESTAMP_NTZ) AS starttime,
    CAST(f.endtime AS TIMESTAMP_NTZ) AS endtime,
    CAST(f.sapsii AS INTEGER) AS sapsii,
    CAST(f.sapsii_prob AS DOUBLE) AS sapsii_prob,
    CAST(f.age_score AS INTEGER) AS age_score,
    CAST(f.hr_score AS INTEGER) AS hr_score,
    CAST(f.sysbp_score AS INTEGER) AS sysbp_score,
    CAST(f.temp_score AS INTEGER) AS temp_score,
    CAST(f.pao2fio2_score AS INTEGER) AS pao2fio2_score,
    CAST(f.uo_score AS INTEGER) AS uo_score,
    CAST(f.bun_score AS INTEGER) AS bun_score,
    CAST(f.wbc_score AS INTEGER) AS wbc_score,
    CAST(f.potassium_score AS INTEGER) AS potassium_score,
    CAST(f.sodium_score AS INTEGER) AS sodium_score,
    CAST(f.bicarbonate_score AS INTEGER) AS bicarbonate_score,
    CAST(f.bilirubin_score AS INTEGER) AS bilirubin_score,
    CAST(f.gcs_score AS INTEGER) AS gcs_score,
    CAST(f.comorbidity_score AS INTEGER) AS comorbidity_score,
    CAST(f.admissiontype_score AS INTEGER) AS admissiontype_score,
    f.encounter_key AS encounter_key,
    f.icu_encounter_key AS icu_encounter_key,
    f.patient_key AS patient_key
FROM final_rows AS f
;
