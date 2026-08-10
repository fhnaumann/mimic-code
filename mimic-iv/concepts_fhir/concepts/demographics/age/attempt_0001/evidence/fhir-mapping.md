# FHIR Mapping: `demographics/age`

## Source → FHIR Resource Mapping

| Source Table | FHIR Resource | Key Filter |
|---|---|---|
| `mimiciv_hosp.patients` | `Patient` | none |
| `mimiciv_hosp.admissions` | `Encounter` | `identifier.system = 'http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp'` |

## Column Mappings

### Representable Columns

| Source Column | FHIRPath | Output Name | Type |
|---|---|---|---|
| `subject_id` | Via join: Patient side `getResourceKey()`, Encounter side `subject.getReferenceKey(Patient)` | `subject_id` | STRING (UUID) |
| `hadm_id` | `identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp').value` | `hadm_id` | STRING |
| `admittime` | `period.start` → `CAST(... AS TIMESTAMP_NTZ)` | `admittime` | TIMESTAMP_NTZ |
| `age` | `YEAR(CAST(period.start AS TIMESTAMP_NTZ)) - YEAR(CAST(birthDate AS TIMESTAMP_NTZ))` | `age` | INTEGER |

### Unrepresentable Columns (FHIR coverage gap)

| Source Column | Reason | Output |
|---|---|---|
| `anchor_age` | No FHIR element. `Patient.birthDate` stores only the year difference `anchor_year - anchor_age`; the pair is collapsed. | `CAST(NULL AS SMALLINT)` |
| `anchor_year` | Same collapse. Heuristic via `MIN(year(Encounter.period.start))` is approximate (~99%). | `CAST(NULL AS SMALLINT)` |

## Probe Results

- **100 Patients**, birth years 2030–2136 (shifted)
- **275 hospital encounters** (filtered from 637 by `encounter-hosp` identifier)
- **Identifier system:** `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp`
- **Period.start:** 275/275 populated
- **Year-subtraction age:** 275/275 produce sensible ages (range 21–93, mean 62.7)
- **No coding/terminology fields** in this concept

## MIMIC_NOTES.md Entries Used

1. `Patient.birthDate` encodes the anchor pair (lines 86–119) — explains unrepresentable columns
2. FHIR datetimes carry offset → `CAST(... AS TIMESTAMP_NTZ)` (lines 160–198)
3. Encounter has three identifier systems → filter by `encounter-hosp` (lines 201–221)
4. No MIMIC-specific extensions on Patient (lines 34–57)