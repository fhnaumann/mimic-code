# FHIR Prober Evidence: `age` (demographics/age)

**Date:** 2026-08-07
**Concept:** demographics/age
**Natural key:** `hadm_id` (single-column)

---

## 1. MIMIC_NOTES.md entries consulted

The following entries changed or informed mapping decisions:

- **`Patient.birthDate` encodes the anchor pair** — birthDate.year == anchor_year - anchor_age holds for 100/100 demo patients. This simplifies the age computation to `year(admittime) - year(birthDate)`, avoiding the need to reconstruct anchor_age/anchor_year from extensions.
- **FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ** — period.start is ISO-8601 with offset (e.g. `2180-05-06T22:23:00-04:00`). For age we only need the year, so `SUBSTR(period.start,1,4)` or `CAST(period.start AS TIMESTAMP_NTZ)` then `YEAR(...)`.
- **Encounter has three identifier systems — class discriminates none** — hospital admissions must be filtered by `identifier.system = '.../encounter-hosp'` (value = hadm_id). Unfiltered, the Encounter table mixes ICU, ED, and hosp streams.
- **Extensions are not a column — use `extension(url)` in FHIRPath** — confirmed: no anchor_age/anchor_year extension exists on Patient. Only us-core-race, us-core-birthsex, us-core-ethnicity.
- **Identifier spine** — Patient identifier system `.../identifier/patient` (value = subject_id), Encounter hosp system `.../identifier/encounter-hosp` (value = hadm_id).

---

## 2. Encounter (admissions) mapping

| Probe | Result |
|-------|--------|
| Total hosp encounters in demo | 275 (matching 275 `mimiciv_hosp.admissions` rows) |
| Identifier system | `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` |
| Identifier value | MIMIC `hadm_id` as integer (e.g. `22595853`) |
| subject.reference format | `Patient/<UUID>` (e.g. `Patient/0a8eebfd-a352-522e-89f0-1d4a13abdebc`) |
| period.start format | ISO-8601 with offset, e.g. `2180-05-06T22:23:00-04:00` |
| class codes observed | `AMB`, `EMER`, `OBSENC`, `SS` — all present in hosp stream |
| Encounter FHIR UUID | Unique per row (not derived from hadm_id) |

### ViewDefinition columns needed for Encounter

| FHIRPath | Name | Type | Notes |
|----------|------|------|-------|
| `getResourceKey()` | `encounter_id` | VARCHAR | FHIR UUID |
| `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value` | `hadm_id` | VARCHAR | Natural key; filter: `WHERE system = '...encounter-hosp'` |
| `subject.getReferenceKey(Patient)` | `patient_id` | VARCHAR | FHIR UUID reference |
| `period.start` | `period_start` | VARCHAR | ISO-8601 with offset; requires CAST to TIMESTAMP_NTZ for date arithmetic |

---

## 3. Patient mapping

| Probe | Result |
|-------|--------|
| Total patients in demo | 100 (matching 100 `mimiciv_hosp.patients` rows) |
| Identifier system | `http://mimic.mit.edu/fhir/mimic/identifier/patient` |
| Identifier value | MIMIC `subject_id` as integer (e.g. `10007795`) |
| birthDate format | ISO-8601 date string (e.g. `2083-04-10`) — year encodes the anchor pair |
| gender | `male` / `female` |
| anchor_age extension | NOT present on Patient (only us-core-race, us-core-birthsex, us-core-ethnicity) |
| anchor_year extension | NOT present on Patient |

### Verification: birthDate encodes anchor pair

- **100/100** demo patients: `birthDate.year == anchor_year - anchor_age`
- Verified via DuckDB join of FHIR Patient (identifier.value = 10007795) ↔ oracle patients (subject_id = 10007795)

### ViewDefinition columns needed for Patient

| FHIRPath | Name | Type | Notes |
|----------|------|------|-------|
| `getResourceKey()` | `patient_id` | VARCHAR | FHIR UUID |
| `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/patient').value` | `subject_id` | VARCHAR | For join to oracle |
| `birthDate` | `birth_date` | VARCHAR | Date string; extract year for age computation |
| `gender` | `gender` | VARCHAR | Not needed for age computation |

---

## 4. Age computation

### Formula

The canonical SQL computes:
```sql
pa.anchor_age + (YEAR(ad.admittime) - pa.anchor_year) AS age
```

Since `Patient.birthDate.year == anchor_year - anchor_age` (100/100 verified), the equivalent FHIR expression is:

```
YEAR(Encounter.period.start) - YEAR(Patient.birthDate)
```

### Verification

**275/275** demo hospital encounters matched exactly between:
- FHIR expression: `YEAR(CAST(period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(birthDate AS DATE))`
- Oracle expression: `anchor_age + (YEAR(admittime) - anchor_year)`

### Datetime handling

Per MIMIC_NOTES.md, period.start is ISO-8601 with offset. The safest approach:
- For year extraction: `SUBSTR(period.start, 1, 4)` (simple, no cast needed)
- Or: `YEAR(CAST(period.start AS TIMESTAMP_NTZ))` (handles all formats per MIMIC_NOTES.md)

Both produce the same year for all 275 demo rows.

---

## 5. Source column → FHIR mapping table

| Source column | Source table | FHIR resource | FHIRPath | Output name | Notes |
|---|---|---|---|---|---|
| `subject_id` | `admissions` | Encounter → Patient | `subject.getReferenceKey(Patient)` | `patient_id` | References Patient UUID |
| `subject_id` | `patients` | Patient | `identifier.where(system='.../patient').value` | `subject_id` | For join/verification |
| `hadm_id` | `admissions` | Encounter | `identifier.where(system='.../encounter-hosp').value` | `hadm_id` | Natural key of the output |
| `admittime` | `admissions` | Encounter | `period.start` | `period_start` | ISO-8601 with offset; CAST to TIMESTAMP_NTZ |
| `anchor_age` | `patients` | — | Not directly representable | — | Encoded in `Patient.birthDate.year` as `anchor_year - anchor_age` |
| `anchor_year` | `patients` | — | Not directly representable | — | Encoded in `Patient.birthDate.year` as `anchor_year - anchor_age` |
| `age` (computed) | — | — | `YEAR(CAST(period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(birthDate AS DATE))` | `age` | Verified 275/275 against oracle |

---

## 6. Gaps / Notes

1. **anchor_age and anchor_year are not directly representable in FHIR.** They are not stored as extensions on Patient. The only way to recover them is via the equation `anchor_year - anchor_age = birthDate.year`, which gives their difference but not their individual values. For the `age` concept, this is sufficient — the formula `year(admittime) - year(birthDate)` produces the correct result without needing the individual components.

2. **No terminology resolution needed.** This concept is a purely numeric computation with no coded fields.

3. **Delta warehouse has stale Parquet files from previous versions.** DuckDB's `read_parquet` glob reads all files including removed ones, producing 3× duplication (1911 rows instead of 637). The Spark/Delta `read.delta` correctly reads only the latest version. This is a DuckDB-probe artifact, not a dataset quirk, so it does not merit a MIMIC_NOTES.md entry.

4. **The ViewDefinition must project Encounter (hosp) and Patient separately**, then the derived SQL JOINs them. The concept is a cross-resource age computation, not a single-resource projection.

---

## 7. MIMIC_NOTES.md updates made

**None.** All findings confirmed existing entries:
- `Patient.birthDate` encodes the anchor pair (100/100 verified)
- Encounter identifier systems (275 hosp encounters filtered)
- FHIR datetime offset (period.start format confirmed)
- No anchor_age/anchor_year extension on Patient (confirmed)