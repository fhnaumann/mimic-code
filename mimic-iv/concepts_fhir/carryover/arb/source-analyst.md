# Source analysis — medication/arb (angiotensin II receptor blockers)

Canonical source: `mimic-iv/concepts/medication/arb.sql`
DAG SHA256: `e24b91d1ecf8eaef598129b7e9cf14e21b2ff27491407c08fbb07efab9b35d97` (matches live file)
DAG node: level 0, `dependencies: []`, `dependents: []`. No `mimiciv_derived` dependencies.

This is a **medication-name (free-text) concept** — like `acei` and `antibiotic`,
it filters on the `prescriptions.drug` text column by name/`LIKE` patterns, NOT on
any itemid code. There are no coded itemids anywhere in the SQL.

## 1. Table references

| Schema | Table | Alias | Role |
|---|---|---|---|
| `mimiciv_hosp` | `prescriptions` | `pr` | source of final output rows (appears as `physionet-data.mimiciv_hosp.prescriptions` in canonical BigQuery form; maps to `mimiciv_hosp.prescriptions`) |
| `mimiciv_hosp` | `prescriptions` | (none, in `arb_drug` CTE) | source of drug-name matching |

Note: the `physionet-data.mimiciv_hosp.prescriptions` prefix is the canonical
MIMIC BigQuery table reference. In this repo's DuckDB dialect the schema is
`mimiciv_hosp`.

## 2. Column list (final output)

| Column | Source | Type (inferred) | Notes |
|---|---|---|---|
| `subject_id` | `pr.subject_id` | INTEGER | |
| `hadm_id` | `pr.hadm_id` | INTEGER | |
| `arb` | `pr.drug` (aliased `arb`) | VARCHAR/TEXT | the source free-text drug name |
| `starttime` | `pr.starttime` | TIMESTAMP | prescription start |
| `stoptime` | `pr.stoptime` | TIMESTAMP | prescription stop |

CTE `arb_drug` columns: `drug` (VARCHAR), `arb` (INTEGER flag 0/1).

## 3. Filters (WHERE / CASE predicates)

**Primary filter — the drug-name matching.** A `CASE` in the `arb_drug` CTE sets
`arb = 1` when `UPPER(drug)` matches **any** of the following 16 `LIKE` patterns
(8 generic + 8 brand). These are case-insensitive substring matches (applied to
`UPPER(drug)` with uppercase tokens). Names verbatim:

```
LIKE '%AZILSARTAN%'   OR LIKE '%EDARBI%'
OR LIKE '%CANDESARTAN%' OR LIKE '%ATACAND%'
OR LIKE '%IRBESARTAN%' OR LIKE '%AVAPRO%'
OR LIKE '%LOSARTAN%'   OR LIKE '%COZAAR%'
OR LIKE '%OLMESARTAN%' OR LIKE '%BENICAR%'
OR LIKE '%TELMISARTAN%' OR LIKE '%MICARDIS%'
OR LIKE '%VALSARTAN%'  OR LIKE '%DIOVAN%'
OR LIKE '%SACUBITRIL%' OR LIKE '%ENTRESTO%'
```

**Final WHERE:** `arb_drug.arb = 1` — i.e. matched at least one of the above
patterns.

**No time-window filters.** No start/stop date bounds. **No itemid / code
filters.** No `drug_type` filter (unlike some other medication concepts).

## 4. Joins

`INNER JOIN arb_drug ON pr.drug = arb_drug.drug` — a keyed inner join on the
exact `drug` text value. Because `arb_drug` is `SELECT DISTINCT drug` + the flag,
this join expands each prescription row whose drug text appears in `arb_drug` to
exactly one output row (the arb_drug set holds each distinct drug name once, and
its `arb` flag value is 1 for matches). Effectively: keep `prescriptions` rows
whose `drug` is in the matched-name set.

## 5. `mimiciv_derived` dependencies

**None.** Level-0 leaf concept. `dependencies: []` in the DAG.

## 6. Aggregations / window functions

- `SELECT DISTINCT` in the `arb_drug` CTE (deduplicates by `drug`).
- No `GROUP BY`, no window functions, no `MIN/MAX/AVG`, no `ARRAY_AGG`.

## 7. Literal code set — verbatim

There are **no itemid / ICD codes** in this concept. The "code set" is the
free-text medication-name filter (Section 3). The source column filtered
(`mimiciv_hosp.prescriptions.drug`) is the name text; the downstream FHIR
representation of that text is described in MIMIC_NOTES.md:

- Hospital `prescriptions.drug` is preserved as
  `Medication.identifier.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name').value`.
- Multi-row `pharmacy_id` groups are represented as medication-mix resources; the
  source drug names survive as `Medication.ingredient.itemReference` → component
  `Medication` carrying the name identifier. A port must handle both the direct
  component reference and the mix-to-ingredient reference (see MIMIC_NOTES
  "Prescription Medication.code prefers NDC/formulary; the source drug name is in
  an identifier").
- MIMIC_NOTES also notes `Medication.code.coding.display` and route displays are
  NULL; filter/join on system + code/identifier value, and the source
  `drug_type` is not retained as a FHIR element.

The literal name-substring tokens a port must reproduce (verbatim from SQL,
already listed in Section 3) feed a single binary output membership decision per
prescription. This is a **name-match concept, not a code-match concept**; the
prober must confirm the name system/identifier values in the served data (per the
`acei` carryover pattern), and the implementer must filter on those
identifier/name values with the same substring case-insensitivity.

## Natural-key implications

Output rows: one per matching `prescriptions` row (per `(subject_id, hadm_id,
drug, starttime, stoptime)`). A likely natural key for the full-data keyed diff
is `(subject_id, hadm_id)` + a time/drug disambiguator (e.g. `starttime`, or
`drug`+`starttime`); no single identity column is unique across a 300k-patient
cohort. Key must be anchored by `subject_id`/`hadm_id` per MIMIC_NOTES. No key
should be derived from demo alone.

## FHIR-touch points relevant to the prober/implementer

- Hospital prescription streams already ported (e.g. `acei`) establish the
  name-identifier/mix handling; `arb` follows the same pattern but with its own
  name-substring set.
- Datetimes (`starttime`, `stoptime`) must be cast to `TIMESTAMP_NTZ` (MIMIC_NOTES:
  FHIR datetimes carry an offset; DST-gap +1h shifts on `MedicationRequest`
  validity endpoints per `fhir_medication_request.sql:43-44`).
- `subject_id`/`hadm_id` come from `identifier.value` (STRING) → cast to INTEGER.

## Caveats / dead filters

- None: this concept has no itemid-based dead filters (unlike `bg`'s `50807`).
  All name tokens are live text matches against served medication-name data.

## Source analyst verdict

Single-table (mimiciv_hosp.prescriptions), name-matched, no dependencies, no
aggregation beyond `DISTINCT`, no time window. Port is entirely about
reproducing the 16 drug-name substring patterns against the served medication
name data and emitting the 5 columns.
