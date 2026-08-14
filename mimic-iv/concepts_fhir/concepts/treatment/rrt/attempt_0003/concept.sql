WITH ce AS (
    SELECT
        o.encounter_key,
        COALESCE(
            TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ),
            TRY_CAST(o.effective_period_start AS TIMESTAMP_NTZ)
        ) AS charttime,
        CASE
            WHEN o.item_code IN ('226118', '227357', '225725') THEN 1
            WHEN o.item_code IN (
                '226499', '224154', '225810', '225959', '227639', '225183',
                '227438', '224191', '225806', '225807', '228004', '228005',
                '228006', '224144', '224145', '224149', '224150', '224151',
                '224152', '224153', '224404', '224406', '226457'
            ) THEN 1
            WHEN o.item_code IN (
                '224135', '224139', '224146', '225323', '225740', '225776',
                '225951', '225952', '225953', '225954', '225956', '225958',
                '225961', '225963', '225965', '225976', '225977', '227124',
                '227290', '227638', '227640', '227753'
            ) THEN 1
            ELSE 0
        END AS dialysis_present,
        CASE
            WHEN o.item_code = '225965' AND o.string_value = 'In use' THEN 1
            WHEN o.item_code IN (
                '226499', '224154', '225183', '227438', '224191', '225806',
                '225807', '228004', '228005', '228006', '224144', '224145',
                '224153', '226457'
            ) THEN 1
            ELSE 0
        END AS dialysis_active,
        CASE
            WHEN o.item_code = '227290' THEN o.string_value
            WHEN o.item_code IN (
                '225810', '225806', '225807', '227639', '225959', '225951',
                '225952', '225961', '225953', '225963', '225965', '227638',
                '227640'
            ) THEN 'Peritoneal'
            WHEN o.item_code = '226499' THEN 'IHD'
            ELSE NULL
        END AS dialysis_type
    FROM rrt_observation o
    WHERE o.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items'
      AND o.item_code IN (
          '226118', '227357', '225725', '226499', '224154', '225810',
          '227639', '225183', '227438', '224191', '225806', '225807',
          '228004', '228005', '228006', '224144', '224145', '224149',
          '224150', '224151', '224152', '224153', '224404', '224406',
          '226457', '225959', '224135', '224139', '224146', '225323',
          '225740', '225776', '225951', '225952', '225953', '225954',
          '225956', '225958', '225961', '225963', '225965', '225976',
          '225977', '227124', '227290', '227638', '227640', '227753'
      )
      AND (o.quantity_value IS NOT NULL OR o.string_value IS NOT NULL)
), mv_ranges AS (
    SELECT
        m.encounter_key,
        TRY_CAST(m.effective_period_start AS TIMESTAMP_NTZ) AS starttime,
        COALESCE(
            TRY_CAST(m.effective_period_end AS TIMESTAMP_NTZ),
            TRY_CAST(m.effective_datetime AS TIMESTAMP_NTZ)
        ) AS endtime,
        1 AS dialysis_present,
        1 AS dialysis_active,
        'CRRT' AS dialysis_type
    FROM rrt_medication_administration m
    WHERE m.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu'
      AND m.item_code IN ('227536', '227525')
      AND CAST(m.dose_value AS DOUBLE) > 0
    UNION DISTINCT
    SELECT
        p.encounter_key,
        TRY_CAST(p.performed_period_start AS TIMESTAMP_NTZ) AS starttime,
        COALESCE(
            TRY_CAST(p.performed_period_end AS TIMESTAMP_NTZ),
            TRY_CAST(p.performed_datetime AS TIMESTAMP_NTZ)
        ) AS endtime,
        1 AS dialysis_present,
        CASE
            WHEN p.item_code NOT IN ('224270', '225436') THEN 1 ELSE 0
        END AS dialysis_active,
        CASE
            WHEN p.item_code = '225441' THEN 'IHD'
            WHEN p.item_code = '225802' THEN 'CRRT'
            WHEN p.item_code = '225803' THEN 'CVVHD'
            WHEN p.item_code = '225805' THEN 'Peritoneal'
            WHEN p.item_code = '225809' THEN 'CVVHDF'
            WHEN p.item_code = '225955' THEN 'SCUF'
            ELSE NULL
        END AS dialysis_type
    FROM rrt_procedure p
    WHERE p.code_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-items'
      AND p.item_code IN (
          '225441', '225802', '225803', '225805',
          '224270', '225809', '225955', '225436'
      )
), stg0 AS (
    SELECT
        encounter_key,
        charttime,
        dialysis_present,
        dialysis_active,
        dialysis_type
    FROM ce
    WHERE dialysis_present = 1
    UNION DISTINCT
    SELECT
        encounter_key,
        starttime AS charttime,
        dialysis_present,
        dialysis_active,
        dialysis_type
    FROM mv_ranges
)
SELECT
    CAST(e.stay_id_str AS INTEGER) AS stay_id,
    CAST(stg0.charttime AS TIMESTAMP_NTZ) AS charttime,
    CAST(COALESCE(mv.dialysis_present, stg0.dialysis_present) AS INTEGER) AS dialysis_present,
    CAST(COALESCE(mv.dialysis_active, stg0.dialysis_active) AS INTEGER) AS dialysis_active,
    CAST(COALESCE(mv.dialysis_type, stg0.dialysis_type) AS VARCHAR(255)) AS dialysis_type
FROM stg0
INNER JOIN rrt_encounter e
    ON stg0.encounter_key = e.encounter_key
LEFT JOIN mv_ranges mv
    ON stg0.encounter_key = mv.encounter_key
   AND stg0.charttime >= mv.starttime
   AND stg0.charttime <= mv.endtime;
