"""Targeted probes for age-concept FHIR mappings."""
import json, sys
sys.path.insert(0, "/Users/nau025/Documents/mimic-code/src")

from mimic_utils.embedded_runner import EmbeddedExecutor

WAREHOUSE = "/Users/nau025/warehouses/mimic-iv-demo/delta"

executor = EmbeddedExecutor(WAREHOUSE)
spark = executor.spark

patient = spark.read.format("delta").load(f"{WAREHOUSE}/Patient.parquet")
patient.createOrReplaceTempView("p_raw")
encounter = spark.read.format("delta").load(f"{WAREHOUSE}/Encounter.parquet")
encounter.createOrReplaceTempView("e_raw")

# Probe A: Identifier system suffixes only
print("=== A: Identifier system suffixes ===")
spark.sql("""
    SELECT system
    FROM (SELECT DISTINCT idents.system AS system
          FROM e_raw LATERAL VIEW EXPLODE(identifier) AS idents) sub
    ORDER BY system
""").show(truncate=False)

# Probe B: Year-subtraction age for hosp encounters (20 sample rows)
print("\n=== B: Year-subtraction age sample ===")
spark.sql("""
    SELECT p.id AS patient_id,
           YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ)) AS birth_year,
           REGEXP_EXTRACT(e.subject.reference, 'Patient/(.+)', 1) AS subj_uuid,
           CAST(e.period.start AS TIMESTAMP_NTZ) AS period_start,
           YEAR(CAST(e.period.start AS TIMESTAMP_NTZ)) AS admission_year,
           YEAR(CAST(e.period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ)) AS computed_age
    FROM e_raw e
    JOIN p_raw p ON REGEXP_EXTRACT(e.subject.reference, 'Patient/(.+)', 1) = p.id
    LATERAL VIEW EXPLODE(e.identifier) AS idents
    WHERE idents.system LIKE '%encounter-hosp'
    ORDER BY p.id
    LIMIT 20
""").show(truncate=False)

# Probe C: Aggregate stats
print("\n=== C: Aggregate stats ===")
spark.sql("""
    SELECT COUNT(DISTINCT p.id) AS patient_count,
           COUNT(*) AS hosp_encounter_count,
           MIN(YEAR(CAST(e.period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ))) AS min_age,
           MAX(YEAR(CAST(e.period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ))) AS max_age,
           ROUND(AVG(YEAR(CAST(e.period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ))), 1) AS avg_age
    FROM e_raw e
    JOIN p_raw p ON REGEXP_EXTRACT(e.subject.reference, 'Patient/(.+)', 1) = p.id
    LATERAL VIEW EXPLODE(e.identifier) AS idents
    WHERE idents.system LIKE '%encounter-hosp'
""").show(truncate=False)

# Probe D: Full age distribution
print("\n=== D: Age distribution ===")
spark.sql("""
    SELECT computed_age, COUNT(*) AS cnt
    FROM (SELECT YEAR(CAST(e.period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(p.birthDate AS TIMESTAMP_NTZ)) AS computed_age
          FROM e_raw e
          JOIN p_raw p ON REGEXP_EXTRACT(e.subject.reference, 'Patient/(.+)', 1) = p.id
          LATERAL VIEW EXPLODE(e.identifier) AS idents
          WHERE idents.system LIKE '%encounter-hosp') sub
    GROUP BY computed_age
    ORDER BY computed_age
""").show(truncate=False)

# Probe E: Subject reference population
print("\n=== E: Subject ref completeness ===")
spark.sql("""
    SELECT CASE WHEN e.subject.reference IS NOT NULL THEN 'populated' ELSE 'null' END AS ref_status,
           COUNT(*) AS cnt
    FROM e_raw e
    LATERAL VIEW EXPLODE(e.identifier) AS idents
    WHERE idents.system LIKE '%encounter-hosp'
    GROUP BY CASE WHEN e.subject.reference IS NOT NULL THEN 'populated' ELSE 'null' END
""").show(truncate=False)

# Probe F: Period.start population
print("\n=== F: Period start null check ===")
spark.sql("""
    SELECT CASE WHEN e.period.start IS NOT NULL THEN 'populated' ELSE 'null' END AS start_status,
           COUNT(*) AS cnt
    FROM e_raw e
    LATERAL VIEW EXPLODE(e.identifier) AS idents
    WHERE idents.system LIKE '%encounter-hosp'
    GROUP BY CASE WHEN e.period.start IS NOT NULL THEN 'populated' ELSE 'null' END
""").show(truncate=False)

# Probe G: Verify identifier value type
print("\n=== G: Identifier value type ===")
spark.sql("""
    SELECT TYPEOF(idents.value) AS value_type, COUNT(*) AS cnt
    FROM e_raw
    LATERAL VIEW EXPLODE(identifier) AS idents
    WHERE idents.system LIKE '%encounter-hosp'
    GROUP BY TYPEOF(idents.value)
""").show(truncate=False)

# Probe H: Total count (should be 275 hosp encounters)
print("\n=== H: Total hosp encounters ===")
spark.sql("""
    SELECT COUNT(DISTINCT e.id) AS unique_hosp_encounters
    FROM e_raw e
    LATERAL VIEW EXPLODE(e.identifier) AS idents
    WHERE idents.system LIKE '%encounter-hosp'
""").show(truncate=False)

# Probe I: Null hadm_id check
print("\n=== I: Null hadm_id check ===")
spark.sql("""
    SELECT COUNT(*) AS total,
           SUM(CASE WHEN idents.value IS NULL THEN 1 ELSE 0 END) AS null_values
    FROM e_raw e
    LATERAL VIEW EXPLODE(e.identifier) AS idents
    WHERE idents.system LIKE '%encounter-hosp'
""").show(truncate=False)

executor.close()
print("\n=== Probe complete ===")