# Source analysis: `nsaid`

## Source and DAG identity

- Concept stem: `nsaid`.
- Canonical SQL: `mimic-iv/concepts/medication/nsaid.sql`.
- The SQL source SHA256 is `5289cf2b0e5c6e1f05030c843560ad36c10c03303492d5cadf60acace92aeccc`, matching the `nsaid` node in `mimic-iv/concept_dag/concept_dag.json`.
- DAG level: `0`.
- DAG dependencies: none (`dependencies: []`); there is no `mimiciv_derived` dependency and no derived concept needs to be ported first.
- The DAG lists `nsaid` as having no dependents.

## Tables and references

The canonical SQL uses one physical source table, scanned twice:

1. `mimiciv_hosp.prescriptions` (written in the SQL as ``physionet-data.mimiciv_hosp.prescriptions``) in the `nsaid_drug` CTE's `FROM` clause, lines 27-28.
2. `mimiciv_hosp.prescriptions` again as alias `pr` in the final query's `FROM` clause, lines 36-37.

The final query also joins the intermediate CTE `nsaid_drug`; this is not a physical table or a `mimiciv_derived` dependency.

No `mimiciv_icu` table and no table in the `mimiciv_derived` schema is referenced.

The checked MIMIC-IV schema defines `mimiciv_hosp.prescriptions` with `subject_id INTEGER NOT NULL`, `hadm_id INTEGER NOT NULL`, `starttime TIMESTAMP(3)`, `stoptime TIMESTAMP(3)`, `drug_type VARCHAR(20) NOT NULL`, and `drug VARCHAR(255) NOT NULL`; the BigQuery schema expresses the corresponding fields as `INT64`, `DATETIME`, and `STRING`.

## CTE and column analysis

### `nsaid_drug` CTE

The CTE executes:

```sql
SELECT DISTINCT
    drug,
    CASE ... END AS nsaid
FROM `physionet-data.mimiciv_hosp.prescriptions`
```

Referenced columns and inferred types:

- `drug`: `VARCHAR(255)` / `STRING`, the source free-text medication name. It is selected, used as the argument to `UPPER`, and used by every `LIKE` predicate. The source schema marks it non-null.
- `UPPER(drug)`: string expression used only for case normalization before matching; it is not output as a separate column.
- `nsaid`: integer discriminator produced by the `CASE`, always the literal integer `1` or `0` for a non-null source `drug` (and also `0` through `ELSE` if a null were encountered). It is selected into the CTE and used by the final `WHERE`.

`DISTINCT` applies to the complete pair `(drug, nsaid)`. Since the discriminator is deterministic for a given exact `drug` string, the CTE has at most one row for each distinct source drug string.

### Final output

The final `SELECT` returns these five columns, in this order:

| Output column | Source/expression | Inferred type | Behavior |
|---|---|---|---|
| `subject_id` | `pr.subject_id` | `INTEGER` / `INT64` | Required source patient identifier, projected unchanged. |
| `hadm_id` | `pr.hadm_id` | `INTEGER` / `INT64` | Required source hospital-admission identifier, projected unchanged. |
| `nsaid` | `pr.drug AS nsaid` | `VARCHAR(255)` / `STRING` | The original source drug name, not the CTE's integer flag. |
| `starttime` | `pr.starttime` | nullable `TIMESTAMP(3)` / `DATETIME` | Projected unchanged; no cast or time transformation in this SQL. |
| `stoptime` | `pr.stoptime` | nullable `TIMESTAMP(3)` / `DATETIME` | Projected unchanged; no cast or time transformation in this SQL. |

The CTE's `nsaid` integer flag is an intermediate column only; it is not emitted. The final output column with the same name is the drug string.

Other `prescriptions` fields, including `pharmacy_id`, `poe_id`, `poe_seq`, `order_provider_id`, `drug_type`, `formulary_drug_cd`, `gsn`, `ndc`, `prod_strength`, `form_rx`, `dose_val_rx`, `dose_unit_rx`, `form_val_disp`, `form_unit_disp`, `doses_per_24_hrs`, and `route`, are not selected, filtered, joined, grouped, or otherwise referenced by this SQL.

## Filters and predicates

### Drug classification predicates

The CTE's `CASE` assigns `nsaid = 1` when `UPPER(drug)` satisfies any of the following substring predicates. The surrounding `%` characters are literal SQL `LIKE` wildcards, so each match may occur anywhere in the drug string. Matching is made case-insensitive by applying `UPPER` to `drug`.

These are the complete literal drug predicate set, copied verbatim from the SQL:

```text
UPPER(drug) LIKE '%ASPIRIN%'
UPPER(drug) LIKE '%BROMFENAC%'
UPPER(drug) LIKE '%CELECOXIB%'
UPPER(drug) LIKE '%DICLOFENAC%'
UPPER(drug) LIKE '%DIFLUNISAL%'
UPPER(drug) LIKE '%ETODOLAC%'
UPPER(drug) LIKE '%FENOPROFEN%'
UPPER(drug) LIKE '%FLURBIPROFEN%'
UPPER(drug) LIKE '%IBUPROFEN%'
UPPER(drug) LIKE '%INDOMETHACIN%'
UPPER(drug) LIKE '%KETOPROFEN%'
UPPER(drug) LIKE '%MEFENAMIC ACID%'
UPPER(drug) LIKE '%MELOXICAM%'
UPPER(drug) LIKE '%NABUMETONE%'
UPPER(drug) LIKE '%NAPROXEN%'
UPPER(drug) LIKE '%NEPAFENAC%'
UPPER(drug) LIKE '%OXAPROZIN%'
UPPER(drug) LIKE '%PIROXICAM%'
UPPER(drug) LIKE '%SULINDAC%'
UPPER(drug) LIKE '%TOLMETIN%'
```

Each predicate filters/classifies `mimiciv_hosp.prescriptions.drug` and feeds the CTE output discriminator `nsaid`. The first matching `WHEN` returns `1`; because all branches return the same value, overlapping patterns do not change the result. A drug matching none of the literals receives `ELSE 0`.

### Final `WHERE`

The only `WHERE` predicate in the canonical SQL is:

```sql
nsaid_drug.nsaid = 1
```

It filters the CTE's integer discriminator and therefore retains only prescription rows whose exact `drug` value was classified by one of the 20 literal substring predicates. There is no `WHERE` clause in the CTE.

There are no itemid predicates, ICD predicates, formal terminology codes, code-version predicates, time windows, dose/value constraints, null checks, or exclusions on `drug_type`, route, NDC, formulary code, or any other prescription field.

## Join analysis

The final query uses one join:

```sql
FROM `physionet-data.mimiciv_hosp.prescriptions` pr
INNER JOIN nsaid_drug
    ON pr.drug = nsaid_drug.drug
```

- Join type: `INNER JOIN`.
- Join condition: exact equality of the raw source drug string, `pr.drug = nsaid_drug.drug`. The join does not compare `UPPER(pr.drug)` and does not join on patient, admission, pharmacy, time, or any medication code.
- Joined relation: the `nsaid_drug` CTE, which contains one row per distinct raw drug string because of `DISTINCT`.
- Consequence: a final `pr` row joins to at most one CTE row. In the unchanged source table, every non-null `pr.drug` has a CTE row because both sides scan `mimiciv_hosp.prescriptions`; the effective inclusion restriction is the final `nsaid_drug.nsaid = 1` filter.

## Aggregations and relational operations

- `SELECT DISTINCT` is the only deduplication operation, and it occurs inside `nsaid_drug` on the `(drug, nsaid)` projection.
- There is no `GROUP BY`, aggregate function (`MIN`, `MAX`, `AVG`, `ARRAY_AGG`, etc.), or window function.
- The final query has no `DISTINCT`, so multiple qualifying source prescription rows remain multiple output rows even if their five projected values are equal.

## Output grain and key

The intended output grain is one row per source `mimiciv_hosp.prescriptions` row whose `drug` contains one of the listed NSAID substrings under the `UPPER`/`LIKE` rules. The CTE join does not fan out that grain because it is distinct by drug.

The raw table schema declares a source primary key `(pharmacy_id, drug_type, drug)` (checked in `buildmimic/postgres/constraint.sql`). The canonical output does not project `pharmacy_id` or `drug_type`, so that source key is not preserved in the output. There is no explicit output key in the SQL, and `(subject_id, hadm_id, nsaid, starttime, stoptime)` must not be assumed unique. Distinct source rows can collapse to the same visible five-column tuple, particularly because `pharmacy_id` and `drug_type` are omitted.

`drug` is both the classification input and a source-key component; the final alias `nsaid` carries that string forward. `subject_id` and `hadm_id` carry patient/admission context. `starttime` and `stoptime` carry the source prescription interval but do not control inclusion.

## Datetime and null behavior

- `starttime` and `stoptime` are directly selected from `prescriptions`; this SQL neither filters them nor performs `COALESCE`, `CAST`, interval arithmetic, timezone conversion, validity checks, or ordering.
- Source `starttime` and `stoptime` are nullable, so a qualifying row with either source value `NULL` remains in the final result with that output column `NULL`. Reversed or otherwise invalid intervals are also not excluded or repaired by this SQL.
- `drug`, `subject_id`, and `hadm_id` are non-null in the checked source schema. The `CASE` nevertheless has an `ELSE 0`, so classification is explicitly non-match for any value that satisfies no predicate.
- The source SQL uses de-identified prescription wall-clock datetimes as stored; any offset formatting, DST-gap normalization, or omission of invalid/incomplete validity periods is a downstream FHIR ETL/representation behavior, not behavior performed by this concept SQL. The curated notes document that prescription FHIR validity periods are written only for complete non-reversed intervals and that DST-gap wall times can be shifted; those facts must not be mistaken for source-side filters.

## Literal code/predicate specification

This concept has no numeric itemid set, ICD code plus version set, NDC set, formulary-code set, or other formal coding-system filter. Its complete source-defined specification is the 20 verbatim free-text `LIKE` literals listed above. They all operate on `mimiciv_hosp.prescriptions.drug` and feed `nsaid_drug.nsaid`, which is then filtered by the exact integer literal `1` in the final `WHERE`.

The exact filter literal in the final `WHERE` is:

```text
nsaid_drug.nsaid = 1
```

The output drug value is `pr.drug` (aliased `nsaid`); it is not replaced by a normalized drug label or code. No dead numeric code filter is present in this SQL.

## Semantically essential inputs

The following inputs can change inclusion, row identity/multiplicity, or a clinically meaningful output and must be traced by downstream mapping/probing:

1. `mimiciv_hosp.prescriptions.drug`: controls all 20 substring branches, the intermediate `nsaid` discriminator, the exact join back to the prescription rows, final row inclusion, and the emitted `nsaid` drug-name value. Its case-normalized value controls classification, while the original exact string controls the join and output.
2. `mimiciv_hosp.prescriptions.subject_id`: required patient identifier emitted as `subject_id`.
3. `mimiciv_hosp.prescriptions.hadm_id`: required hospital-admission identifier emitted as `hadm_id`.
4. `mimiciv_hosp.prescriptions.starttime`: nullable prescription start datetime emitted as `starttime`; it does not filter rows but is clinically meaningful interval output and may be part of any downstream row alignment.
5. `mimiciv_hosp.prescriptions.stoptime`: nullable prescription stop datetime emitted as `stoptime`; same qualification as `starttime`.
6. `pharmacy_id` and `drug_type`: not referenced by the SQL and not output, but together with `drug` they form the checked source primary key `(pharmacy_id, drug_type, drug)`. Their omission means they remain relevant to source-row multiplicity and explain why the five-column output has no guaranteed unique key. `drug_type` is not an NSAID exclusion in this concept.

The remaining prescription columns are semantically unused by this SQL: changing them cannot alter its predicates, join, grouping, output values, or output row count except through an external change to the source table's rows.

## Relevant notes and scope boundary

I read the prescription-related sections of `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`, and the relevant provisional medication fragment `mimic-iv/concepts_fhir/MIMIC_NOTES.d/arb.md`. The notes establish downstream facts without changing the source analysis: prescription Medication resources retain the original `drug` name in a medication-name identifier even when `Medication.code` prefers NDC or formulary coding; pharmacy groups can be represented as medication mixes with repeated ingredient references; `drug_type` is not retained; and incomplete/reversed prescription intervals can be absent from `MedicationRequest.dispenseRequest.validityPeriod`. The curated datetime note also documents possible DST-gap shifts. These are FHIR-side representability considerations, not additional predicates in `nsaid.sql`.

This artifact intentionally contains source analysis only. It does not author a ViewDefinition, derived SQL, terminology mapping, or clinical decision.

## Evidence

- Read: `mimic-iv/concepts/medication/nsaid.sql`, `mimic-iv/concept_dag/concept_dag.json`, `mimic-iv/buildmimic/postgres/create.sql`, `mimic-iv/buildmimic/postgres/constraint.sql`, `mimic-iv/buildmimic/bigquery/schemas/hosp/prescriptions.json`, `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`, and the relevant `MIMIC_NOTES.d` medication fragment.
- Checked: the DAG node exists at level 0 with no dependencies; the SQL SHA256 matches the DAG; all physical `FROM`/`JOIN` references, selected/referenced columns, predicates, exact literal drug patterns, join type/condition, null/datetime behavior, deduplication, and source/output grain were traced.
- Result: `nsaid` is a level-0, single-table hospital-prescription concept that emits qualifying prescription rows using 20 exact free-text substring predicates and preserves the source identifiers and nullable prescription times without additional transformation.
