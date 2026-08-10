# Source Analysis: `age`

**Concept:** `demographics/age`
**SQL Source:** `mimic-iv/concepts/demographics/age.sql`
**Analyst:** source-analyst
**Date:** 2026-08-07

---

## 1. Table References

| # | Schema | Table | Alias | Description |
|---|--------|-------|-------|-------------|
| 1 | `mimiciv_hosp` | `admissions` | `ad` | Hospital admission records |
| 2 | `mimiciv_hosp` | `patients` | `pa` | Patient demographic records (anchor_age, anchor_year) |

No `mimiciv_icu` tables are referenced.

---

## 2. Columns Used, per Table

### `admissions` (alias `ad`)
| Column | Type (inferred) | Purpose |
|--------|-----------------|---------|
| `subject_id` | INTEGER | Patient identifier — join key |
| `hadm_id` | INTEGER | Admission identifier — natural key of the output |
| `admittime` | TIMESTAMP | Admission datetime — used as the reference point for age calculation |

### `patients` (alias `pa`)
| Column | Type (inferred) | Purpose |
|--------|-----------------|---------|
| `subject_id` | INTEGER | Patient identifier — join key |
| `anchor_age` | SMALLINT | Patient's age in the anchor year |
| `anchor_year` | SMALLINT | Shifted year representing the patient's time reference |

---

## 3. Output Columns (SELECT list)

| Position | Expression | Alias | Type (inferred) |
|----------|-----------|-------|-----------------|
| 1 | `ad.subject_id` | `subject_id` | INTEGER |
| 2 | `ad.hadm_id` | `hadm_id` | INTEGER |
| 3 | `ad.admittime` | `admittime` | TIMESTAMP |
| 4 | `pa.anchor_age` | `anchor_age` | SMALLINT |
| 5 | `pa.anchor_year` | `anchor_year` | SMALLINT |
| 6 | `pa.anchor_age + DATETIME_DIFF(ad.admittime, DATETIME(pa.anchor_year, 1, 1, 0, 0, 0), YEAR)` | `age` | BIGINT (computed) |

---

## 4. Computed Column: `age`

**Formula:**
```sql
pa.anchor_age + DATETIME_DIFF(ad.admittime, DATETIME(pa.anchor_year, 1, 1, 0, 0, 0), YEAR) AS age
```

**Breakdown:**
1. `DATETIME(pa.anchor_year, 1, 1, 0, 0, 0)` — constructs a datetime for January 1 of the anchor year (midnight).
2. `DATETIME_DIFF(ad.admittime, ..., YEAR)` — computes the whole number of years between the admission datetime and the anchor year start.
3. `pa.anchor_age + ...` — adds that year difference to the patient's age at anchor time.

**Clinical meaning:** Since MIMIC-IV shifts dates for de-identification, a patient's real age cannot be computed from calendar dates alone. The `anchor_age` field records the patient's age at the anchor year. The formula computes admission age as:
> `age = anchor_age + (admission_year - anchor_year)`

This produces the patient's integer age (in years) at the time of hospital admission.

**Note on BigQuery dialect:** The SQL uses BigQuery-specific functions `DATETIME_DIFF` and `DATETIME()`. For the MIMIC-on-FHIR port, these must be translated to equivalent Spark/Pathling or DuckDB functions (e.g., `DATE_DIFF` or `EXTRACT(YEAR FROM ...)` or `(YEAR(admittime) - anchor_year) + anchor_age`).

---

## 5. Join Conditions

| Type | Left | Right | Condition | Cardinality |
|------|------|-------|-----------|-------------|
| INNER JOIN | `admissions ad` | `patients pa` | `ad.subject_id = pa.subject_id` | One admission → one patient; INNER means only admissions with a matching patient record are included. |

This is a simple **single-condition inner join** on `subject_id`. No additional filters are applied.

---

## 6. Filters / WHERE Clauses

**None.** The SQL has no `WHERE` clause. Every row in `admissions` that has a matching `patients` record is included. This means:
- All hospital admissions are included.
- Admissions for patients without a `patients` record (should not exist referentially) are excluded by the INNER JOIN.
- No date-range filtering, no adult-only filtering, no exclusion of test patients.

The output row count of `431,231` (from the oracle manifest) matches the total number of admissions in MIMIC-IV, confirming no filtering.

---

## 7. Dependencies on `mimiciv_derived`

**None.** The concept is Level 0 in the DAG. It only references raw tables from `mimiciv_hosp`:
- `mimiciv_hosp.admissions`
- `mimiciv_hosp.patients`

No intermediate `mimiciv_derived` views are required.

---

## 8. Coding Systems / Terminology

**None.** This concept is a purely numeric computation. No `itemid`, `icd_code`, `icd_version`, `loinc_code`, or any other code system is referenced. No terminology resolution is needed.

---

## 9. Natural Key

Per the oracle manifest, the natural key is **`hadm_id`** (single-column key). The SQL output indeed has one row per `hadm_id` since:
- `admissions.hadm_id` is the primary key of the `admissions` table (one row per admission).
- The INNER JOIN to `patients` does not fan out rows because the join is on `subject_id`, which is 1:1 between admissions and patients.
- No aggregation or GROUP BY is applied.

---

## 10. Any Edge Cases or Notes

1. **Shifted dates:** Because MIMIC-IV uses shifted years for de-identification (`anchor_year`), the computed `age` is an integer approximation. The `DATETIME_DIFF(..., YEAR)` function counts whole year boundaries, meaning a patient admitted on Dec 31, 2154 with anchor_year 2153 and anchor_age 60 would have age = 60 + 1 = 61, even if their birthday was Jan 2, 2154. This is the canonical MIMIC behaviour.

2. **No age capping:** The canonical query does not cap age at 89 or any other value (as some derived concepts do). Raw computed age is output directly.

3. **No null handling:** If `anchor_age` or `anchor_year` were NULL (they shouldn't be per the MIMIC schema), the entire `age` expression would be NULL.

4. **BigQuery-specific functions:** `DATETIME_DIFF` and `DATETIME()` are BigQuery built-ins. The port must replace these with equivalent Spark SQL, Pathling FHIR SQL, or DuckDB functions.

---

## Summary

The `age` concept joins `admissions` to `patients` on `subject_id` and computes the patient's age in years at admission using the formula `anchor_age + (admission_year - anchor_year)`. No filtering, no coding systems, and no `mimiciv_derived` dependencies — it is a pure Level 0 concept. The natural key is `hadm_id`. The only porting challenge is converting the BigQuery date arithmetic to equivalent SQL for the target engine.