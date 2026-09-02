-- Readability copy -- not the artifact a server loads.
--
-- Library.oasis.json in this directory is authoritative. This SQL is
-- the decoded form of its content.data, byte-identical to the sql-text
-- extension beside it.
--
-- HAND-EDITED: this concept carries the Pathling SQL-allowlist rewrites
-- (TIMESTAMPDIFF/TIMESTAMPADD, LATERAL VIEW, HAVING). It is NOT what
-- `mimic-utils metrics-finalize` produces -- see PATHLING_WORKAROUNDS.md.

WITH icu AS (
    SELECT
        i.icu_encounter_key,
        i.patient_key,
        i.hospital_encounter_key AS encounter_key,
        i.stay_id_str,
        TRY_CAST(i.intime_datetime AS TIMESTAMP_NTZ) AS intime
    FROM icu_encounter AS i
    WHERE i.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
        AND i.stay_id_str IS NOT NULL
), hospital AS (
    SELECT
        h.encounter_key,
        h.patient_key,
        h.hadm_id_str,
        TRY_CAST(h.period_start AS TIMESTAMP_NTZ) AS admittime,
        h.priority_system,
        h.priority_code
    FROM hospital_encounter AS h
    WHERE h.hadm_id_str IS NOT NULL
), surgflag AS (
    SELECT
        h.encounter_key,
        MAX(
            CASE
                WHEN hs.service_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-services'
                    AND LOWER(hs.service_code) LIKE '%surg%' THEN 1
                WHEN hs.service_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-services'
                    AND hs.service_code = 'ORTHO' THEN 1
                ELSE 0
            END
        ) AS surgical
    FROM hospital AS h
    LEFT JOIN hospital_service AS hs
        ON h.encounter_key = hs.encounter_key
    GROUP BY h.encounter_key
), vent AS (
    SELECT
        i.icu_encounter_key,
        MAX(
            CASE
                WHEN v.icu_encounter_key IS NOT NULL THEN 1
                ELSE 0
            END
        ) AS vent
    FROM icu AS i
    LEFT JOIN ventilation AS v
        ON i.icu_encounter_key = v.icu_encounter_key
        AND v.ventilation_status = 'InvasiveVent'
        AND (
            (
                v.starttime >= i.intime
                AND v.starttime <= i.intime + INTERVAL 1 DAY
            )
            OR (
                v.endtime >= i.intime
                AND v.endtime <= i.intime + INTERVAL 1 DAY
            )
            OR (
                v.starttime <= i.intime
                AND v.endtime >= i.intime + INTERVAL 1 DAY
            )
        )
    GROUP BY i.icu_encounter_key
), cohort AS (
    SELECT
        p.subject_id_str,
        h.hadm_id_str,
        i.stay_id_str,
        i.patient_key,
        h.encounter_key,
        i.icu_encounter_key,
        i.intime,
        CAST((UNIX_TIMESTAMP(DATE_TRUNC('MINUTE', i.intime)) - UNIX_TIMESTAMP(DATE_TRUNC('MINUTE', h.admittime))) / 60 AS BIGINT) AS preiculos,
        ag.age,
        gcs.gcs_min,
        vital.heart_rate_max,
        vital.heart_rate_min,
        vital.mbp_max,
        vital.mbp_min,
        vital.resp_rate_max,
        vital.resp_rate_min,
        vital.temperature_max,
        vital.temperature_min,
        vent.vent AS mechvent,
        uo.urineoutput,
        CASE
            WHEN h.priority_system = 'http://terminology.hl7.org/CodeSystem/v3-ActPriority'
                AND h.priority_code = 'EL'
                AND sf.surgical = 1 THEN 1
            WHEN h.priority_system IS NULL
                OR h.priority_code IS NULL
                OR sf.surgical IS NULL THEN NULL
            ELSE 0
        END AS electivesurgery
    FROM icu AS i
    INNER JOIN hospital AS h
        ON i.encounter_key = h.encounter_key
    INNER JOIN patient AS p
        ON i.patient_key = p.patient_key
        AND p.subject_id_str IS NOT NULL
    LEFT JOIN age AS ag
        ON h.encounter_key = ag.encounter_key
    LEFT JOIN surgflag AS sf
        ON h.encounter_key = sf.encounter_key
    LEFT JOIN first_day_gcs AS gcs
        ON i.icu_encounter_key = gcs.icu_encounter_key
    LEFT JOIN first_day_vitalsign AS vital
        ON i.icu_encounter_key = vital.icu_encounter_key
    LEFT JOIN first_day_urine_output AS uo
        ON i.icu_encounter_key = uo.icu_encounter_key
    LEFT JOIN vent
        ON i.icu_encounter_key = vent.icu_encounter_key
), scorecomp AS (
    SELECT
        co.subject_id_str,
        co.hadm_id_str,
        co.stay_id_str,
        co.patient_key,
        co.encounter_key,
        co.icu_encounter_key,
        co.age,
        co.preiculos,
        co.gcs_min,
        co.heart_rate_max,
        co.heart_rate_min,
        co.mbp_max,
        co.mbp_min,
        co.resp_rate_max,
        co.resp_rate_min,
        co.temperature_max,
        co.temperature_min,
        co.urineoutput,
        co.mechvent,
        co.electivesurgery,
        CASE
            WHEN preiculos IS NULL THEN NULL
            WHEN preiculos < 10.2 THEN 5
            WHEN preiculos < 297 THEN 3
            WHEN preiculos < 1440 THEN 0
            WHEN preiculos < 18708 THEN 2
            ELSE 1
        END AS preiculos_score,
        CASE
            WHEN age IS NULL THEN NULL
            WHEN age < 24 THEN 0
            WHEN age <= 53 THEN 3
            WHEN age <= 77 THEN 6
            WHEN age <= 89 THEN 9
            WHEN age >= 90 THEN 7
            ELSE 0
        END AS age_score,
        CASE
            WHEN gcs_min IS NULL THEN NULL
            WHEN gcs_min <= 7 THEN 10
            WHEN gcs_min < 14 THEN 4
            WHEN gcs_min = 14 THEN 3
            ELSE 0
        END AS gcs_score,
        CASE
            WHEN heart_rate_max IS NULL THEN NULL
            WHEN heart_rate_max > 125 THEN 6
            WHEN heart_rate_min < 33 THEN 4
            WHEN heart_rate_max >= 107 AND heart_rate_max <= 125 THEN 3
            WHEN heart_rate_max >= 89 AND heart_rate_max <= 106 THEN 1
            ELSE 0
        END AS heart_rate_score,
        CASE
            WHEN mbp_min IS NULL THEN NULL
            WHEN mbp_min < 20.65 THEN 4
            WHEN mbp_min < 51 THEN 3
            WHEN mbp_max > 143.44 THEN 3
            WHEN mbp_min >= 51 AND mbp_min < 61.33 THEN 2
            ELSE 0
        END AS mbp_score,
        CASE
            WHEN resp_rate_min IS NULL THEN NULL
            WHEN resp_rate_min < 6 THEN 10
            WHEN resp_rate_max > 44 THEN 9
            WHEN resp_rate_max > 30 THEN 6
            WHEN resp_rate_max > 22 THEN 1
            WHEN resp_rate_min < 13 THEN 1
            ELSE 0
        END AS resp_rate_score,
        CASE
            WHEN temperature_max IS NULL THEN NULL
            WHEN temperature_max > 39.88 THEN 6
            WHEN temperature_min >= 33.22 AND temperature_min <= 35.93 THEN 4
            WHEN temperature_max >= 33.22 AND temperature_max <= 35.93 THEN 4
            WHEN temperature_min < 33.22 THEN 3
            WHEN temperature_min > 35.93 AND temperature_min <= 36.39 THEN 2
            WHEN temperature_max >= 36.89 AND temperature_max <= 39.88 THEN 2
            ELSE 0
        END AS temp_score,
        CASE
            WHEN urineoutput IS NULL THEN NULL
            WHEN urineoutput < 671.09 THEN 10
            WHEN urineoutput > 6896.80 THEN 8
            WHEN urineoutput >= 671.09 AND urineoutput <= 1426.99 THEN 5
            WHEN urineoutput >= 1427.00 AND urineoutput <= 2544.14 THEN 1
            ELSE 0
        END AS urineoutput_score,
        CASE
            WHEN mechvent IS NULL THEN NULL
            WHEN mechvent = 1 THEN 9
            ELSE 0
        END AS mechvent_score,
        CASE
            WHEN electivesurgery IS NULL THEN NULL
            WHEN electivesurgery = 1 THEN 0
            ELSE 6
        END AS electivesurgery_score
    FROM cohort AS co
), score AS (
    SELECT
        s.*,
        COALESCE(age_score, 0)
            + COALESCE(preiculos_score, 0)
            + COALESCE(gcs_score, 0)
            + COALESCE(heart_rate_score, 0)
            + COALESCE(mbp_score, 0)
            + COALESCE(resp_rate_score, 0)
            + COALESCE(temp_score, 0)
            + COALESCE(urineoutput_score, 0)
            + COALESCE(mechvent_score, 0)
            + COALESCE(electivesurgery_score, 0) AS oasis
    FROM scorecomp AS s
), final_rows AS (
    SELECT
        s.subject_id_str,
        s.hadm_id_str,
        s.stay_id_str,
        s.oasis,
        1 / (1 + EXP(-(-6.1746 + 0.1275 * s.oasis))) AS oasis_prob,
        s.age,
        s.age_score,
        s.preiculos,
        s.preiculos_score,
        s.gcs_min AS gcs,
        s.gcs_score,
        CASE
            WHEN s.heart_rate_max IS NULL THEN NULL
            WHEN s.heart_rate_max > 125 THEN s.heart_rate_max
            WHEN s.heart_rate_min < 33 THEN s.heart_rate_min
            WHEN s.heart_rate_max >= 107 AND s.heart_rate_max <= 125 THEN s.heart_rate_max
            WHEN s.heart_rate_max >= 89 AND s.heart_rate_max <= 106 THEN s.heart_rate_max
            ELSE (s.heart_rate_min + s.heart_rate_max) / 2
        END AS heartrate,
        s.heart_rate_score,
        CASE
            WHEN s.mbp_min IS NULL THEN NULL
            WHEN s.mbp_min < 20.65 THEN s.mbp_min
            WHEN s.mbp_min < 51 THEN s.mbp_min
            WHEN s.mbp_max > 143.44 THEN s.mbp_max
            WHEN s.mbp_min >= 51 AND s.mbp_min < 61.33 THEN s.mbp_min
            ELSE (s.mbp_min + s.mbp_max) / 2
        END AS meanbp,
        s.mbp_score,
        CASE
            WHEN s.resp_rate_min IS NULL THEN NULL
            WHEN s.resp_rate_min < 6 THEN s.resp_rate_min
            WHEN s.resp_rate_max > 44 THEN s.resp_rate_max
            WHEN s.resp_rate_max > 30 THEN s.resp_rate_max
            WHEN s.resp_rate_max > 22 THEN s.resp_rate_max
            WHEN s.resp_rate_min < 13 THEN s.resp_rate_min
            ELSE (s.resp_rate_min + s.resp_rate_max) / 2
        END AS resprate,
        s.resp_rate_score,
        CASE
            WHEN s.temperature_max IS NULL THEN NULL
            WHEN s.temperature_max > 39.88 THEN s.temperature_max
            WHEN s.temperature_min >= 33.22 AND s.temperature_min <= 35.93 THEN s.temperature_min
            WHEN s.temperature_max >= 33.22 AND s.temperature_max <= 35.93 THEN s.temperature_max
            WHEN s.temperature_min < 33.22 THEN s.temperature_min
            WHEN s.temperature_min > 35.93 AND s.temperature_min <= 36.39 THEN s.temperature_min
            WHEN s.temperature_max >= 36.89 AND s.temperature_max <= 39.88 THEN s.temperature_max
            ELSE (s.temperature_min + s.temperature_max) / 2
        END AS temp,
        s.temp_score,
        s.urineoutput,
        s.urineoutput_score,
        s.mechvent,
        s.mechvent_score,
        s.electivesurgery,
        s.electivesurgery_score,
        s.encounter_key,
        s.icu_encounter_key,
        s.patient_key
    FROM score AS s
)
SELECT
    CAST(f.oasis AS INTEGER) AS oasis,
    CAST(f.oasis_prob AS DOUBLE) AS oasis_prob,
    CAST(f.age AS BIGINT) AS age,
    CAST(f.age_score AS INTEGER) AS age_score,
    CAST(f.preiculos AS BIGINT) AS preiculos,
    CAST(f.preiculos_score AS INTEGER) AS preiculos_score,
    CAST(f.gcs AS FLOAT) AS gcs,
    CAST(f.gcs_score AS INTEGER) AS gcs_score,
    CAST(f.heartrate AS DOUBLE) AS heartrate,
    CAST(f.heart_rate_score AS INTEGER) AS heart_rate_score,
    CAST(f.meanbp AS DOUBLE) AS meanbp,
    CAST(f.mbp_score AS INTEGER) AS mbp_score,
    CAST(f.resprate AS DOUBLE) AS resprate,
    CAST(f.resp_rate_score AS INTEGER) AS resp_rate_score,
    CAST(f.temp AS DOUBLE) AS temp,
    CAST(f.temp_score AS INTEGER) AS temp_score,
    CAST(f.urineoutput AS DOUBLE) AS urineoutput,
    CAST(f.urineoutput_score AS INTEGER) AS urineoutput_score,
    CAST(f.mechvent AS INTEGER) AS mechvent,
    CAST(f.mechvent_score AS INTEGER) AS mechvent_score,
    CAST(f.electivesurgery AS INTEGER) AS electivesurgery,
    CAST(f.electivesurgery_score AS INTEGER) AS electivesurgery_score,
    f.encounter_key AS encounter_key,
    f.icu_encounter_key AS icu_encounter_key,
    f.patient_key AS patient_key
FROM final_rows AS f
;
