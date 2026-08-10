# Source Analysis: `demographics/age`

## 1. Referenced Source Tables

| Schema | Table | Alias |
|--------|-------|-------|
| `mimiciv_hosp` | `admissions` | `ad` |
| `mimiciv_hosp` | `patients` | `pa` |

## 2. Output Columns

| # | Column | Source | Type | Notes |
|---|--------|--------|------|-------|
| 1 | `subject_id` | `admissions` | INT64 | Patient identifier |
| 2 | `hadm_id` | `admissions` | INT64 | Hospital admission identifier |
| 3 | `admittime` | `admissions` | DATETIME | Date/time of hospital admission |
| 4 | `anchor_age` | `patients` | INT64 | Patient's age in the shifted anchor year |
| 5 | `anchor_year` | `patients` | INT64 | Shifted year anchoring the patient's timeline |
| 6 | `age` | *derived* | INT64 | Computed: patient's age at admission time |

## 3. Joins

- `INNER JOIN` `admissions` (`ad`) ON `pat` (`pa`) ON `ad.subject_id = pa.subject_id`

## 4. Filters

None.

## 5. Derived Column: `age`

Expression: `pa.anchor_age + DATETIME_DIFF(ad.admittime, DATETIME(pa.anchor_year, 1, 1, 0, 0, 0), YEAR) AS age`

Semantics: `age = anchor_age + (admission_year - anchor_year)` — the patient's real age at admission, recovered from the shifted dates because both `admittime` and `anchor_year` are shifted by the same offset.

## 6. Dependencies on `mimiciv_derived` Concepts

None. Level 0 concept.

## 7. Category

`demographics`

## 8. Natural Key Candidates

`(subject_id, hadm_id)` — one row per hospital admission per patient.

## 9. Data Type Summary

| Column | Type |
|--------|------|
| `subject_id` | INT64 |
| `hadm_id` | INT64 |
| `admittime` | DATETIME |
| `anchor_age` | INT64 (NULLABLE) |
| `anchor_year` | INT64 |
| `age` | INT64 (computed) |

## 10. Special Notes

- MIMIC-IV uses date shifting for de-identification. `anchor_year` is a shifted year; `anchor_age` is the patient's real age at that shifted year.
- The formula cancels out the shift: `age = anchor_age + (admission_year - anchor_year)` recovers the real age at admission.
- No coding systems or terminology references.