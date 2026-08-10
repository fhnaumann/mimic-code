# Source Analysis: `acei`

**Concept:** `medication/acei`
**SQL Source:** `mimic-iv/concepts/medication/acei.sql`
**Analyst:** source-analyst
**Date:** 2026-08-07
**SHA256 (verified against DAG):** `6a5ec32282f6e5207d33818b689fb1c52d41c075f36a0dbc6eeb135afb510110` — matches `concept_dag.json` node, source has not moved.

---

## 1. Table References

| # | Schema | Table | Alias | Description |
|---|--------|-------|-------|-------------|
| 1 | `mimiciv_hosp` | `prescriptions` | (CTE source, unaliased) | Distinct drug names + ACEI flag |
| 2 | `mimiciv_hosp` | `prescriptions` | `pr` | Main scan — the actual prescription rows |

The table appears twice but it is **the same table twice** (self-join); there are no other tables. No `mimiciv_icu` tables. BigQuery syntax `physionet-data.mimiciv_hosp.prescriptions` must be rewritten to `mimiciv_hosp.prescriptions` for Spark/DuckDB.

---

## 2. Columns Used, per Table

### `mimiciv_hosp.prescriptions` (source DDL: `buildmimic/postgres/create.sql:296-320`)
| Column | Type (DDL) | Purpose |
|--------|-----------|---------|
| `subject_id` | INTEGER NOT NULL | Patient identifier — output column 1 |
| `hadm_id` | INTEGER NOT NULL | Admission identifier — output column 2 |
| `drug` | VARCHAR(255) NOT NULL | Free-text drug name — **the only drug identifier used**; drives the ACEI flag and is emitted as the output `acei` column |
| `starttime` | TIMESTAMP(3) | Prescription start — output column 4 |
| `stoptime` | TIMESTAMP(3) | Prescription stop — output column 5 |

Unused but present in the table: `pharmacy_id` (PK part), `poe_id`, `poe_seq`, `order_provider_id`, `drug_type`, `formulary_drug_cd`, `gsn`, `ndc`, `prod_strength`, `form_rx`, `dose_val_rx`, `dose_unit_rx`, `form_val_disp`, `form_unit_disp`, `doses_per_24_hrs`, `route`. The concept selects **none** of these. Notably `drug_type` is NOT filtered — MAIN/ADDITIVE/etc. rows are all kept. `ndc`/`gsn` are not used.

Primary key of the table (constraint.sql:118-121): `(pharmacy_id, drug_type, drug)` — so two rows with identical `(subject_id, hadm_id, drug, starttime, stoptime)` can exist (differing only in `pharmacy_id`); this is why the output has no unique key (see §9).

---

## 3. Output Columns (SELECT list, main query)

| Position | Expression | Alias | Type (inferred) | Type (oracle manifest) |
|----------|-----------|-------|-----------------|------------------------|
| 1 | `pr.subject_id` | `subject_id` | INTEGER | INTEGER |
| 2 | `pr.hadm_id` | `hadm_id` | INTEGER | INTEGER |
| 3 | `pr.drug` | `acei` | VARCHAR(255) | VARCHAR |
| 4 | `pr.starttime` | `starttime` | TIMESTAMP | TIMESTAMP |
| 5 | `pr.stoptime` | `stoptime` | TIMESTAMP | TIMESTAMP |

**Naming quirk (important):** the output column `acei` contains the **drug name string** (`pr.drug AS acei`), NOT the 0/1 flag. The flag (`acei_drug.acei`) is computed only to filter rows; it never appears in the output. A faithful port must emit the drug name under a column named `acei`.

Manifest row count (full oracle): **112,014**. Demo prescriptions table: 18,087 rows; full: 20,292,611 rows (buildmimic validate.sql).

---

## 4. Filters / WHERE Clauses

There is exactly **one semantic filter**, applied through the join:

1. **ACEI name matching (CTE CASE, then `WHERE acei_drug.acei = 1`):** `UPPER(drug)` matched as a **case-insensitive substring** against ten patterns:
   - `%BENAZEPRIL%`, `%CAPTOPRIL%`, `%ENALAPRIL%`, `%FOSINOPRIL%`, `%LISINOPRIL%`, `%MOEXIPRIL%`, `%PERINDOPRIL%`, `%QUINAPRIL%`, `%RAMIPRIL%`, `%TRANDOLAPRIL%`
   - Any match → flag 1, ELSE 0; the WHERE keeps only flag-1 rows.

No time window, no `drug_type` filter, no admission/demographic filter, no NULL exclusion, no explicit exclusion of combination products (e.g. `Captopril-HCTZ` matches `%CAPTOPRIL%` and is included — this is canonical behaviour, not a bug).

`drug` is NOT NULL in the DDL, so the equality join cannot drop rows through NULL key mismatch.

---

## 5. Joins

| Type | Left | Right | Condition | Cardinality |
|------|------|-------|-----------|-------------|
| INNER JOIN | `prescriptions pr` | CTE `acei_drug` (DISTINCT drug names from the same table) | `pr.drug = acei_drug.drug` | Many→1: every ACEI prescription row matches its distinct drug name |

The CTE is `SELECT DISTINCT drug, CASE(...) AS acei` — one row per distinct drug name across the whole table. The join on exact string equality of `drug` plus the `WHERE acei = 1` is functionally equivalent to `WHERE <CASE expression> = 1` applied directly to `pr`; the join does not change row multiplicity (1:1 on the drug-name side per row). Output rows are **not** deduplicated — one output row per matching source prescription row.

---

## 6. Dependencies on `mimiciv_derived`

**None.** Level 0 in the DAG (`dependencies: []`, `dependents: []`). The concept reads only the raw `mimiciv_hosp.prescriptions` table. Nothing else needs to be ported first, and no other concept depends on `acei`.

---

## 7. Aggregations

- **CTE:** `SELECT DISTINCT` over `(drug, CASE flag)` — deduplicates drug names so the flag is computed once per distinct name. No `GROUP BY`, no window functions, no `MIN/MAX/AVG/ARRAY_AGG`.
- **Main query:** no aggregation of any kind; no `GROUP BY`, no `ORDER BY`. Output is a projection of the joined rows.

---

## 8. Coding Systems / Terminology

**No formal coding system is used in the SQL.** There is no `itemid`, `icd_code`/`icd_version`, `loinc_code`, `ndc`, or `gsn` reference — the drug identity is the free-text `drug` VARCHAR column matched with `UPPER LIKE` substring patterns.

Implication for MIMIC-on-FHIR: the FHIR side carries this drug identity in `MedicationAdministration.medication` codings. Two `MIMIC_NOTES.md` entries directly apply:
- **"Medication name codings can have null display but readable code"** — the `mimic-medication-name` system coding has the human-readable drug name in `Coding.code` with a null display; **filter the code, not the display**.
- **"Polymorphic fields mix datatypes across rows — COALESCE them"** — `MedicationAdministration.effective` is sometimes `effective.ofType(dateTime)`, sometimes `effective.ofType(Period).start`; project both variants and COALESCE. `starttime`/`stoptime` map onto the effective Period (`start`/`end`) where present.

The ten ACEI substring patterns are the terminology the port must reproduce — they are text patterns, not codes; the port matches the medication-name coding text with the same `LIKE` predicates (or an equivalent precomputed equivalent-name filter).

---

## 9. Natural Key / Comparison Mode

**No unique key.** The oracle manifest entry for `acei`:
- `comparison: "full_tuple_multiset"`, `key: null`, `key_probes: 6`
- One of the 13 unkeyed concepts (manifest `summary.unkeyed_concepts` includes `acei`).

Why: the table PK is `(pharmacy_id, drug_type, drug)` and the output drops `pharmacy_id`/`drug_type`, so duplicate `(subject_id, hadm_id, drug, starttime, stoptime)` tuples are possible, and `starttime`/`stoptime` are nullable. Any key the port could construct would not be unique on full data.

Consequence (per LOOP_CONTRACT.md): the comparator cannot align rows, so a NULL-for-value divergence lands in `only_oracle` AND `only_candidate` simultaneously; results carry `classification: unavailable_no_key` and route to `review`, where `only_candidate` must be treated as a bug unless positively shown otherwise. The port should still prefer the smallest sensible key-like projection for internal QA, but the diff itself is a full-tuple multiset comparison.

---

## 10. Edge Cases / Notes for the Port

1. **`pr.drug AS acei` mislabel:** the `acei` column carries the drug name. Emitting the 0/1 flag here instead would be a `differing_conflict` on every row.
2. **Substring matching is canonical:** combination products (e.g. `Captropril-HCTZ` via `%CAPTOPRIL%`, `Perindopril Arginine` via `%PERINDOPRIL%`) are included by design. Do not "improve" the match with word boundaries or exclusions.
3. **Case-insensitivity:** `UPPER(drug) LIKE` — the port must apply the same case-folding (or use `ILIKE`-equivalent) so `lisinopril`/`LISINOPRIL`/`Lisinopril` all match.
4. **NULL timestamps:** `starttime`/`stoptime` are nullable (no NOT NULL in DDL); output rows may carry NULL timestamps and must preserve them, not drop the row.
5. **No dedup:** one output row per matching prescription row; do not apply `DISTINCT` to the output.
6. **FHIR resource stream:** hospital-stream `MedicationAdministration` (hosp prescriptions; the concept has no ICU-only scope). Encounter filtering by `identifier.system` = `.../encounter-hosp` may be needed per MIMIC_NOTES "Encounter has three identifier systems"; the prober should confirm how `MedicationAdministration` references its Encounter/Patient in the warehouse.
7. **BigQuery dialect:** `physionet-data.mimiciv_hosp.prescriptions` → `mimiciv_hosp.prescriptions`; no BigQuery-only functions are used (no `DATETIME_DIFF` here — unlike `age`, timestamps pass through unchanged).

---

## Summary

`acei` is a Level-0 concept over the single raw table `mimiciv_hosp.prescriptions` (self-joined to a `SELECT DISTINCT` drug-name CTE). It filters to rows whose `UPPER(drug)` contains one of ten ACEI name substrings, and outputs `subject_id`, `hadm_id`, the **drug name mislabeled `acei`**, `starttime`, `stoptime` — one row per matching prescription, no dedup, no aggregation, no derived dependencies, no coded terminologies. The oracle manifest declares it a **full-tuple-multiset (unkeyed)** comparison with 112,014 rows. The port must reproduce the text-substring ACEI filter against the FHIR `mimic-medication-name` codings and preserve the column-name quirk.
