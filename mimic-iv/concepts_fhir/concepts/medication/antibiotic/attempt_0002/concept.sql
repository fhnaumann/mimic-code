WITH expanded_prescriptions AS (
    SELECT
        mr.patient_key,
        mr.encounter_key,
        mr.pharmacy_id_str,
        mr.medication_key,
        mr.starttime_str,
        mr.stoptime_str,
        mr.route_code,
        mr.route_system,
        m.drug_system,
        m.drug_name
    FROM medication_request mr
    INNER JOIN medication m
        ON mr.medication_key = m.medication_key
    WHERE mr.pharmacy_id_str IS NOT NULL
        AND mr.medication_key IS NOT NULL
        AND m.drug_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name'

    UNION ALL

    SELECT
        mr.patient_key,
        mr.encounter_key,
        mr.pharmacy_id_str,
        mr.medication_key,
        mr.starttime_str,
        mr.stoptime_str,
        mr.route_code,
        mr.route_system,
        m.drug_system,
        m.drug_name
    FROM medication_request mr
    INNER JOIN medication_mix mm
        ON mr.medication_key = mm.mix_key
    INNER JOIN medication m
        ON mm.ingredient_medication_key = m.medication_key
    WHERE mr.pharmacy_id_str IS NOT NULL
        AND mr.medication_key IS NOT NULL
        AND m.drug_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name'
), abx AS (
    SELECT DISTINCT
        drug_name,
        route_code,
        route_system,
        CASE
            WHEN LOWER(drug_name) LIKE '%adoxa%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ala-tet%' THEN 1
            WHEN LOWER(drug_name) LIKE '%alodox%' THEN 1
            WHEN LOWER(drug_name) LIKE '%amikacin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%amikin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%amoxicill%' THEN 1
            WHEN LOWER(drug_name) LIKE '%amphotericin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%anidulafungin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ancef%' THEN 1
            WHEN LOWER(drug_name) LIKE '%clavulanate%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ampicillin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%augmentin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%avelox%' THEN 1
            WHEN LOWER(drug_name) LIKE '%avidoxy%' THEN 1
            WHEN LOWER(drug_name) LIKE '%azactam%' THEN 1
            WHEN LOWER(drug_name) LIKE '%azithromycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%aztreonam%' THEN 1
            WHEN LOWER(drug_name) LIKE '%axetil%' THEN 1
            WHEN LOWER(drug_name) LIKE '%bactocill%' THEN 1
            WHEN LOWER(drug_name) LIKE '%bactrim%' THEN 1
            WHEN LOWER(drug_name) LIKE '%bactroban%' THEN 1
            WHEN LOWER(drug_name) LIKE '%bethkis%' THEN 1
            WHEN LOWER(drug_name) LIKE '%biaxin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%bicillin l-a%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cayston%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefazolin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cedax%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefoxitin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ceftazidime%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefaclor%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefadroxil%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefdinir%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefditoren%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefepime%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefotan%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefotetan%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefotaxime%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ceftaroline%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefpodoxime%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefpirome%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefprozil%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ceftibuten%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ceftin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ceftriaxone%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cefuroxime%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cephalexin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cephalothin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cephapririn%' THEN 1
            WHEN LOWER(drug_name) LIKE '%chloramphenicol%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cipro%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ciprofloxacin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%claforan%' THEN 1
            WHEN LOWER(drug_name) LIKE '%clarithromycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cleocin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%clindamycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%cubicin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%dicloxacillin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%dirithromycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%doryx%' THEN 1
            WHEN LOWER(drug_name) LIKE '%doxycy%' THEN 1
            WHEN LOWER(drug_name) LIKE '%duricef%' THEN 1
            WHEN LOWER(drug_name) LIKE '%dynacin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ery-tab%' THEN 1
            WHEN LOWER(drug_name) LIKE '%eryped%' THEN 1
            WHEN LOWER(drug_name) LIKE '%eryc%' THEN 1
            WHEN LOWER(drug_name) LIKE '%erythrocin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%erythromycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%factive%' THEN 1
            WHEN LOWER(drug_name) LIKE '%flagyl%' THEN 1
            WHEN LOWER(drug_name) LIKE '%fortaz%' THEN 1
            WHEN LOWER(drug_name) LIKE '%furadantin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%garamycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%gentamicin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%kanamycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%keflex%' THEN 1
            WHEN LOWER(drug_name) LIKE '%kefzol%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ketek%' THEN 1
            WHEN LOWER(drug_name) LIKE '%levaquin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%levofloxacin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%lincocin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%linezolid%' THEN 1
            WHEN LOWER(drug_name) LIKE '%macrobid%' THEN 1
            WHEN LOWER(drug_name) LIKE '%macrodantin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%maxipime%' THEN 1
            WHEN LOWER(drug_name) LIKE '%mefoxin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%metronidazole%' THEN 1
            WHEN LOWER(drug_name) LIKE '%meropenem%' THEN 1
            WHEN LOWER(drug_name) LIKE '%methicillin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%minocin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%minocycline%' THEN 1
            WHEN LOWER(drug_name) LIKE '%monodox%' THEN 1
            WHEN LOWER(drug_name) LIKE '%monurol%' THEN 1
            WHEN LOWER(drug_name) LIKE '%morgidox%' THEN 1
            WHEN LOWER(drug_name) LIKE '%moxatag%' THEN 1
            WHEN LOWER(drug_name) LIKE '%moxifloxacin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%mupirocin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%myrac%' THEN 1
            WHEN LOWER(drug_name) LIKE '%nafcillin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%neomycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%nicazel doxy 30%' THEN 1
            WHEN LOWER(drug_name) LIKE '%nitrofurantoin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%norfloxacin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%noroxin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ocudox%' THEN 1
            WHEN LOWER(drug_name) LIKE '%ofloxacin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%omnicef%' THEN 1
            WHEN LOWER(drug_name) LIKE '%oracea%' THEN 1
            WHEN LOWER(drug_name) LIKE '%oraxyl%' THEN 1
            WHEN LOWER(drug_name) LIKE '%oxacillin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%pc pen vk%' THEN 1
            WHEN LOWER(drug_name) LIKE '%pce dispertab%' THEN 1
            WHEN LOWER(drug_name) LIKE '%panixine%' THEN 1
            WHEN LOWER(drug_name) LIKE '%pediazole%' THEN 1
            WHEN LOWER(drug_name) LIKE '%penicillin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%periostat%' THEN 1
            WHEN LOWER(drug_name) LIKE '%pfizerpen%' THEN 1
            WHEN LOWER(drug_name) LIKE '%piperacillin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%tazobactam%' THEN 1
            WHEN LOWER(drug_name) LIKE '%primsol%' THEN 1
            WHEN LOWER(drug_name) LIKE '%proquin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%raniclor%' THEN 1
            WHEN LOWER(drug_name) LIKE '%rifadin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%rifampin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%rocephin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%smz-tmp%' THEN 1
            WHEN LOWER(drug_name) LIKE '%septra%' THEN 1
            WHEN LOWER(drug_name) LIKE '%septra ds%' THEN 1
            WHEN LOWER(drug_name) LIKE '%septra%' THEN 1
            WHEN LOWER(drug_name) LIKE '%solodyn%' THEN 1
            WHEN LOWER(drug_name) LIKE '%spectracef%' THEN 1
            WHEN LOWER(drug_name) LIKE '%streptomycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%sulfadiazine%' THEN 1
            WHEN LOWER(drug_name) LIKE '%sulfamethoxazole%' THEN 1
            WHEN LOWER(drug_name) LIKE '%trimethoprim%' THEN 1
            WHEN LOWER(drug_name) LIKE '%sulfatrim%' THEN 1
            WHEN LOWER(drug_name) LIKE '%sulfisoxazole%' THEN 1
            WHEN LOWER(drug_name) LIKE '%suprax%' THEN 1
            WHEN LOWER(drug_name) LIKE '%synercid%' THEN 1
            WHEN LOWER(drug_name) LIKE '%tazicef%' THEN 1
            WHEN LOWER(drug_name) LIKE '%tetracycline%' THEN 1
            WHEN LOWER(drug_name) LIKE '%timentin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%tobramycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%trimethoprim%' THEN 1
            WHEN LOWER(drug_name) LIKE '%unasyn%' THEN 1
            WHEN LOWER(drug_name) LIKE '%vancocin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%vancomycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%vantin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%vibativ%' THEN 1
            WHEN LOWER(drug_name) LIKE '%vibra-tabs%' THEN 1
            WHEN LOWER(drug_name) LIKE '%vibramycin%' THEN 1
            WHEN LOWER(drug_name) LIKE '%zinacef%' THEN 1
            WHEN LOWER(drug_name) LIKE '%zithromax%' THEN 1
            WHEN LOWER(drug_name) LIKE '%zosyn%' THEN 1
            WHEN LOWER(drug_name) LIKE '%zyvox%' THEN 1
            ELSE 0
        END AS antibiotic
    FROM expanded_prescriptions
    WHERE route_system = 'http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-route'
        -- prescriptions.drug_type NOT IN ('BASE') is not recoverable: no FHIR
        -- element carries drug_type, and no output column is being estimated.
        AND route_code NOT IN ('OU', 'OS', 'OD', 'AU', 'AS', 'AD', 'TP')
        AND LOWER(route_code) NOT LIKE '%ear%'
        AND LOWER(route_code) NOT LIKE '%eye%'
        AND LOWER(drug_name) NOT LIKE '%cream%'
        AND LOWER(drug_name) NOT LIKE '%desensitization%'
        AND LOWER(drug_name) NOT LIKE '%ophth oint%'
        AND LOWER(drug_name) NOT LIKE '%gel%'
), prescription_rows AS (
    SELECT
        p.patient_key,
        p.encounter_key,
        p.drug_name,
        p.route_code,
        p.starttime_str,
        p.stoptime_str
    FROM expanded_prescriptions p
    INNER JOIN abx
        ON p.drug_name = abx.drug_name
        AND p.route_code = abx.route_code
        AND p.route_system = abx.route_system
    WHERE abx.antibiotic = 1
), parsed_prescriptions AS (
    SELECT
        p.patient_key,
        p.encounter_key,
        p.drug_name,
        p.route_code,
        TRY_CAST(p.starttime_str AS TIMESTAMP_NTZ) AS starttime_ts,
        TRY_CAST(p.stoptime_str AS TIMESTAMP_NTZ) AS stoptime_ts
    FROM prescription_rows p
), parsed_icu AS (
    SELECT
        i.hospital_encounter_key,
        i.stay_id_str,
        TRY_CAST(i.intime_str AS TIMESTAMP_NTZ) AS intime_ts,
        TRY_CAST(i.outtime_str AS TIMESTAMP_NTZ) AS outtime_ts
    FROM encounter_icu i
    WHERE i.stay_id_str IS NOT NULL
), resolved_rows AS (
    SELECT
        p.subject_id_str,
        e.hadm_id_str,
        r.drug_name,
        r.route_code,
        r.starttime_ts,
        r.stoptime_ts,
        i.stay_id_str
    FROM parsed_prescriptions r
    INNER JOIN patient p
        ON r.patient_key = p.patient_key
    INNER JOIN encounter e
        ON r.encounter_key = e.encounter_key
        AND r.patient_key = e.patient_key
    LEFT JOIN parsed_icu i
        ON r.encounter_key = i.hospital_encounter_key
        AND r.starttime_ts >= i.intime_ts
        AND r.starttime_ts < i.outtime_ts
    WHERE e.hadm_id_str IS NOT NULL
)
SELECT
    CAST(subject_id_str AS INTEGER) AS subject_id,
    CAST(hadm_id_str AS INTEGER) AS hadm_id,
    CAST(stay_id_str AS INTEGER) AS stay_id,
    CAST(drug_name AS VARCHAR(255)) AS antibiotic,
    CAST(route_code AS VARCHAR(255)) AS route,
    CAST(starttime_ts AS TIMESTAMP_NTZ) AS starttime,
    CAST(stoptime_ts AS TIMESTAMP_NTZ) AS stoptime
FROM resolved_rows
;
