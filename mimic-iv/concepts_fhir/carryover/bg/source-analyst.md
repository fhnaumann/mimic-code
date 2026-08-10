# Source Analysis: `bg` (blood gases)

**Concept:** `measurement/bg`
**SQL Source:** `mimic-iv/concepts/measurement/bg.sql`
**DAG node:** stem `bg`, path `measurement/bg.sql`, level 0, sha256
`90a7f58852b5af97cfce799e9e76a9754c765e2fb9593860ca6bf85b60a5cd55` — verified
matching the file on disk.
**Oracle manifest:** 27 output columns, 511,637 rows,
`comparison: full_tuple_multiset`, `key: null` (one of the 13 unkeyed
concepts; LOOP_CONTRACT names `bg` as a concept whose demo-derived key is
**not unique on full data** — never key the candidate on
`(subject_id, charttime)` or any demo-derived key; a join on it fans out).
**Analyst:** source-analyst
**Date:** 2026-08-07

---

## 1. Table References

| # | Schema | Table | Alias | Used in CTE | Description |
|---|--------|-------|-------|-------------|-------------|
| 1 | `mimiciv_hosp` | `labevents` | `le` | `bg` | Blood-gas lab measurements (one row per item per specimen) |
| 2 | `mimiciv_icu` | `chartevents` | — | `stg_spo2`, `stg_fio2` | ICU charted vitals: SpO2 (220277) and FiO2 (223835) |

No other tables are referenced. No `mimiciv_derived` tables.

---

## 2. Source Columns Used, per Table

### `mimiciv_hosp.labevents` (alias `le`) — DDL at `buildmimic/postgres/create.sql:165-184`
| Column | Type (DDL) | Used for |
|--------|-----------|----------|
| `subject_id` | INTEGER NOT NULL | output id; join to chartevents in stg2/stg3 |
| `hadm_id` | INTEGER (nullable) | output id; `MAX(hadm_id)` may therefore be NULL |
| `specimen_id` | INTEGER NOT NULL | **GROUP BY key** of the pivot; partitions of both window functions |
| `itemid` | INTEGER NOT NULL | pivot discriminator; `WHERE itemid IN (25 blood-gas ids)` |
| `charttime` | TIMESTAMP | output timestamp; reference point for SpO2 (−2 h) / FiO2 (−4 h) windows |
| `storetime` | TIMESTAMP | `MAX(storetime)` computed in CTE but **dropped** from final output |
| `value` | VARCHAR(200) | text pivots: 52033 → `specimen`, 50807 → `comments` (dropped) |
| `valuenum` | DOUBLE PRECISION | numeric pivots (23 columns) |

### `mimiciv_icu.chartevents` — DDL at `buildmimic/postgres/create.sql:369-383`
| Column | Type (DDL) | Used for |
|--------|-----------|----------|
| `subject_id` | INTEGER NOT NULL | join to bg rows (same patient) |
| `charttime` | TIMESTAMP | window position relative to the blood gas |
| `itemid` | INTEGER NOT NULL | 220277 (SpO2) / 223835 (FiO2) filters |
| `valuenum` | FLOAT | SpO2 `AVG`, FiO2 `MAX(CASE …)` |

`stay_id`, `hadm_id`, `value`, `valueuom`, `storetime`, `warning` exist but are
unused.

---

## 3. Output Columns (final SELECT, order matters) — types from the oracle manifest

| # | Alias | Expression source | Manifest type |
|---|-------|-------------------|---------------|
| 1 | `subject_id` | `stg3.subject_id` | INTEGER |
| 2 | `hadm_id` | `stg3.hadm_id` | INTEGER |
| 3 | `charttime` | `stg3.charttime` | TIMESTAMP |
| 4 | `specimen` | lab 52033 `value` (text) | VARCHAR |
| 5 | `so2` | lab 50817 valuenum | DOUBLE |
| 6 | `po2` | lab 50821 valuenum | DOUBLE |
| 7 | `pco2` | lab 50818 valuenum | DOUBLE |
| 8 | `fio2_chartevents` | chart 223835 (window-joined) | FLOAT |
| 9 | `fio2` | lab 50816 valuenum (unit-normalised) | DOUBLE |
| 10 | `aado2` | lab 50801 valuenum | DOUBLE |
| 11 | `aado2_calc` | computed: `ROUND(CAST((fio2_frac*(760-47) - pco2/0.8 - po2) AS NUMERIC), 4)` | DECIMAL(38,4) |
| 12 | `pao2fio2ratio` | computed: `100 * po2 / fio2_frac` | DOUBLE |
| 13 | `ph` | lab 50820 | DOUBLE |
| 14 | `baseexcess` | lab 50802 | DOUBLE |
| 15 | `bicarbonate` | lab 50803 | DOUBLE |
| 16 | `totalco2` | lab 50804 | DOUBLE |
| 17 | `hematocrit` | lab 50810 | DOUBLE |
| 18 | `hemoglobin` | lab 50811 | DOUBLE |
| 19 | `carboxyhemoglobin` | lab 50805 | DOUBLE |
| 20 | `methemoglobin` | lab 50814 | DOUBLE |
| 21 | `chloride` | lab 50806 | DOUBLE |
| 22 | `calcium` | lab 50808 | DOUBLE |
| 23 | `temperature` | lab 50825 | DOUBLE |
| 24 | `potassium` | lab 50822 | DOUBLE |
| 25 | `sodium` | lab 50824 | DOUBLE |
| 26 | `lactate` | lab 50813 | DOUBLE |
| 27 | `glucose` | lab 50809 | DOUBLE |

**Dropped before output** (computed in CTEs but never selected): `storetime`,
`specimen_id`, `lastrowspo2`, `lastrowfio2`, `comments` (50807), `o2flow`
(50815), `peep` (50819), `requiredo2` (50823). `comments`/`o2flow`/`peep`/
`requiredo2` are commented out of the final SELECT.

---

## 4. CTE flow and Aggregations

```
labevents (25 blood-gas itemids)
  └─ bg:      MAX() pivot, GROUP BY specimen_id          → one row per specimen
  └─ stg_spo2: chartevents 220277, AVG(valuenum) GROUP BY subject_id, charttime
  └─ stg_fio2: chartevents 223835, MAX(CASE…) GROUP BY subject_id, charttime
stg2 = bg LEFT JOIN stg_spo2 (2 h window) + ROW_NUMBER()
stg3 = stg2 LEFT JOIN stg_fio2 (4 h window) + ROW_NUMBER()
final = stg3 filtered to most-recent FiO2
```

- **bg CTE** — 26 `MAX(...)` pivots grouped by `specimen_id`. Relies on the
  invariant that each `specimen_id` has ≤1 measurement per itemid. Two text
  pivots use `value` (52033 specimen, 50807 comments); the rest use `valuenum`
  (with per-item value constraints, §6).
- **stg_spo2** — `AVG(valuenum)` per `(subject_id, charttime)` — comment: "avg
  here is just used to group SpO2 by charttime"; multiple nurse-documented SpO2
  values at one charttime are averaged.
- **stg_fio2** — `MAX(CASE …)` per `(subject_id, charttime)`.
- **Window functions** — `ROW_NUMBER() OVER (PARTITION BY specimen_id ORDER BY
  s.charttime DESC)` twice:
  - `lastrowspo2` in stg2: ranks SpO2 candidates newest-first.
  - `lastrowfio2` in stg3: ranks FiO2 candidates newest-first.
  - A specimen with **no** matching chart row still yields ROW_NUMBER = 1
    (single row in partition), which is how "no SpO2/FiO2 found" survives the
    `= 1` filters — matches the source comments.
- **`aado2_calc`** — `ROUND(CAST(CASE … AS NUMERIC), 4)`; the CASE prefers the
  lab `fio2` (50816), falls back to `fio2_chartevents` (223835); formula
  `(fio2/100)*(760-47) - (pco2/0.8) - po2` (fractional FiO2 × 713 mmHg minus
  pCO2/0.8 minus pO2). NULL if `po2` or `pco2` is NULL.
- **`pao2fio2ratio`** — `100 * po2 / fio2` (lab first, chart fallback); NULL if
  `po2` NULL or neither FiO2 present.

---

## 5. Joins

| Type | Left | Right | Condition |
|------|------|-------|-----------|
| LEFT JOIN | `bg` | `stg_spo2 s1` | `bg.subject_id = s1.subject_id` AND `s1.charttime BETWEEN bg.charttime - 2 h AND bg.charttime` |
| LEFT JOIN | `stg2 bg` | `stg_fio2 s2` | `bg.subject_id = s2.subject_id` AND `s2.charttime BETWEEN bg.charttime - 4 h AND bg.charttime` AND `s2.fio2_chartevents > 0` |

Both are LEFT JOINs keyed by **subject_id + charttime window** (2 h SpO2,
4 h FiO2, both strictly at-or-before the gas). Note these are patient-level
time windows, **not** hospitalization or ICU-stay joins — the SQL comment on
stg2 says "same hospitalization" but the condition itself is only
`subject_id` + time; `hadm_id`/`stay_id` are not join keys.

---

## 6. Filters (WHERE / per-pivot constraints)

1. `bg` CTE: `WHERE le.itemid IN (52033, 50801, 50802, 50803, 50804, 50805,
   50806, 50807, 50808, 50809, 50810, 50811, 50813, 50814, 50815, 50816,
   50817, 50818, 50819, 50820, 50821, 50822, 50823, 50824, 50825)` — the 25
   blood-gas items. Commented-out exclusions: 52390 (chloride WB), 52408
   (potassium WB), 52411 (sodium WB) — whole-blood duplicates deliberately NOT
   included.
2. Per-pivot value constraints inside the `MAX(CASE …)`:
   - glucose (50809): `valuenum <= 10000`
   - hematocrit (50810): `valuenum <= 100`
   - lactate (50813): `valuenum <= 10000`
   - fio2 lab (50816): `> 20 AND <= 100` → as-is; `> 0.2 AND <= 1.0` → ×100
     (unit fix: atmospheric O2 is 20.89 %, so ≤20 is a misplaced O2-flow);
     otherwise NULL
   - so2 (50817): `valuenum <= 100`
   - no constraint on aado2, baseexcess, bicarbonate, totalco2,
     carboxyhemoglobin, chloride, calcium, hemoglobin, methemoglobin, o2flow,
     pco2, peep, ph, po2, potassium, requiredo2, sodium, temperature
3. `stg_spo2`: `WHERE itemid = 220277 AND valuenum > 0 AND valuenum <= 100`
   (SpO2 plausibility).
4. `stg_fio2`: `WHERE itemid = 223835 AND valuenum > 0 AND valuenum <= 100`,
   plus in-CASE: `> 0.2 AND <= 1` → ×100; `> 1 AND < 20` → NULL (O2-flow in
   litres misentered); `>= 20 AND <= 100` → as-is; else NULL.
5. `stg2`: `WHERE bg.po2 IS NOT NULL` — a specimen without a PO2 value is
   dropped (despite the LEFT JOIN).
6. `stg3`: `WHERE bg.lastrowspo2 = 1` — keep only the row with the most recent
   SpO2 (or the no-SpO2 single row).
7. Final: `WHERE lastrowfio2 = 1` — keep only the most recent FiO2 (or the
   no-FiO2 single row).

---

## 7. Dependencies on `mimiciv_derived`

**None.** Level 0 in the DAG (`dependencies: []`). Referenced raw tables only.
Dependents (built on top of bg, must come later): `apsiii`, `first_day_bg`,
`first_day_bg_art`, `first_day_sofa`, `lods`, `sapsii`, `sofa`.

---

## 8. Coding Systems / Terminology

All code references are **hard-coded numeric itemids** — proprietary MIMIC
systems, no ICD/LOINC in the source SQL:

- **Lab itemids** (`mimiciv_hosp.labevents.itemid`): 52033, 50801–50825
  (subset). These resolve via `mimiciv_hosp.d_labitems` (itemid → label/fluid/
  category). **Important dataset fact:** MIMIC-IV 2.2's `d_labitems` has **no
  `loinc_code` column** (canonical `buildmimic/postgres/create.sql:79-85`;
  confirmed by demo DESCRIBE) — v2.2 dropped the LOINC columns, so there is no
  relational LOINC mapping for lab items in this build. Labels (demo): 50801
  Alveolar-arterial Gradient, 50802 Base Excess, 50803 Calculated Bicarbonate
  Whole Blood, 50804 Calculated Total CO2, 50805 Carboxyhemoglobin, 50806
  Chloride Whole Blood, 50808 Free Calcium, 50809 Glucose, 50810 Hematocrit
  Calculated, 50811 Hemoglobin, 50813 Lactate, 50814 Methemoglobin, 50815 O2
  Flow, 50816 Oxygen (= FiO2), 50817 Oxygen Saturation, 50818 pCO2, 50819
  PEEP, 50820 pH, 50821 pO2, 50822 Potassium Whole Blood, 50823 Required O2,
  50824 Sodium Whole Blood, 50825 Temperature, 52033 Specimen Type. Itemid
  50807 (comments) is absent from 2.2 `d_labitems` and from the demo data
  (0 rows) — it is a v1.0 leftover; harmless dead filter.
- **Chart itemids** (`mimiciv_icu.chartevents.itemid`): 220277 "O2 saturation
  pulseoxymetry" (unit %), 223835 "Inspired O2 Fraction" (no unit in
  d_items). These resolve via `mimiciv_icu.d_items`.
- The FHIR side will need the corresponding proprietary code systems
  (`mimic-labevents`-style and `mimic-chartevents-d-items`-style per
  MIMIC_NOTES.md); terminology resolution must not expect LOINC from the
  relational schema.

---

## 9. Natural Key / Comparison Class

**None — unkeyed.** Manifest: `"key": null`, `"comparison":
"full_tuple_multiset"`, `key_probes: 6`. Per LOOP_CONTRACT, `bg` is one of the
concepts whose demo-derived key (e.g. `(subject_id, charttime)`) is **not
unique on full data** — 511,637 rows against a demo-unique key would fan out.
The comparator must use full-tuple multiset comparison; any divergence lands in
`review` with `classification: unavailable_no_key`. Downstream: do not attempt
to pick a key from the SQL; the candidate output has no guaranteed unique key.

---

## 10. Dialect / Porting Notes

- Source SQL is BigQuery dialect: `physionet-data.mimiciv_hosp.labevents`
  (schema.table qualification → `mimiciv_hosp.labevents`),
  `DATETIME_SUB(bg.charttime, INTERVAL '2' HOUR)` / `'4' HOUR`,
  `CAST(... AS NUMERIC)` (→ DECIMAL), `ROUND(x, 4)`.
- `fio2_chartevents` is `FLOAT` in the manifest while every other numeric is
  `DOUBLE` (inherited from `chartevents.valuenum` FLOAT DDL); the candidate
  must reproduce that exact type split or the schema gate fails.
- `aado2_calc` must be `DECIMAL(38,4)` (rounded to 4 dp).
- Output has no `storetime`/`specimen_id` — do not invent extra columns.

---

## 11. Dataset-wide quirks this concept leans on (already in MIMIC_NOTES.md)

- "MIMIC ids live in `identifier.value` as STRINGs" — `subject_id`/`hadm_id`
  must be CAST to INTEGER in the candidate.
- "FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ" — `charttime`.
- "Lab Observation encounter references are incomplete — join by patient and
  time" — the lab half of bg must be joined by patient + effective-time
  window, never by Encounter reference.
- "Blood glucose spans laboratory and ICU chart streams" — 50809 is a blood
  gas glucose (vs urine 51478); bg uses the lab stream only.
- "Categorical chartevents store their label in valueString" — the 52033
  `specimen` text value is expected as a string value in FHIR.
- "Merged Observation profile — discriminate with base bindings" — relevant
  when the prober discriminates lab vs chart Observations.

---

## Summary

`bg` is a Level-0, dependency-free pivot of 25 blood-gas `labevents` itemids
grouped by `specimen_id`, enriched with the most recent ICU-charted SpO2
(220277, 2 h window) and FiO2 (223835, 4 h window), outputting 27 columns
(511,637 rows) including two computed oxygen parameters (`aado2_calc`,
`pao2fio2ratio`). It references only `mimiciv_hosp.labevents` and
`mimiciv_icu.chartevents`; all coding is proprietary numeric itemids; it is an
**unkeyed** concept (full-tuple multiset comparison, review route). Porting
challenges: BigQuery `DATETIME_SUB`/`CAST AS NUMERIC` translation, the
FLOAT-vs-DOUBLE type split, and the absence of any LOINC in MIMIC-IV 2.2.
