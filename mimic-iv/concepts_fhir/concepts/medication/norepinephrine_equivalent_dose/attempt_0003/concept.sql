SELECT
    CAST(e.stay_id_str AS INTEGER) AS stay_id,
    CAST(v.starttime AS TIMESTAMP_NTZ) AS starttime,
    CAST(v.endtime AS TIMESTAMP_NTZ) AS endtime,
    CAST(
        ROUND(
            CAST(
                COALESCE(v.norepinephrine, 0)
                + COALESCE(v.epinephrine, 0)
                + COALESCE(v.phenylephrine / 10, 0)
                + COALESCE(v.dopamine / 100, 0)
                + COALESCE(v.vasopressin * 2.5 / 60, 0)
                AS DECIMAL(38,9)
            ),
            4
        ) AS DECIMAL(38,4)
    ) AS norepinephrine_equivalent_dose,
    v.icu_encounter_key,
    v.patient_key
FROM vasoactive_agent AS v
JOIN encounter_icu AS e
    ON v.icu_encounter_key = e.encounter_key
   AND e.stay_system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu'
WHERE v.norepinephrine IS NOT NULL
    OR v.epinephrine IS NOT NULL
    OR v.phenylephrine IS NOT NULL
    OR v.dopamine IS NOT NULL
    OR v.vasopressin IS NOT NULL;
