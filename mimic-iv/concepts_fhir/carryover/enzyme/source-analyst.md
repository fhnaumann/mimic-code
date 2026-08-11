# Source analysis: `enzyme`

## Source and DAG grounding

- Canonical SQL: `mimic-iv/concepts/measurement/enzyme.sql`.
- The DAG node is `enzyme`, path `measurement/enzyme.sql`, level `0`, with
  SHA256 `5c719b94ec9947366f4eb191687e12f2b80931764272c3c6988506ef716647cd`.
- The DAG lists no dependencies. Its dependents are `first_day_lab`, `sapsii`,
  and `sofa`.
- The canonical file has no CTEs and no reference to `mimiciv_derived`. The
  generated DuckDB/Postgres build materializes the result as
  `mimiciv_derived.enzyme`; that is the output concept, not an input
  dependency.

## Table references

The only `FROM`/`JOIN` reference is:

| SQL clause | Logical schema | Table | Alias | Join type/condition |
|---|---|---|---|---|
| `FROM \`physionet-data.mimiciv_hosp.labevents\` le` | `mimiciv_hosp` | `labevents` | `le` | Base table; no join |

There are no `JOIN` clauses, and the canonical SQL does not read
`d_labitems`, `specimens`, `admissions`, or any other table.

## Source columns and output types

The source DDL defines `subject_id`, `specimen_id`, and `itemid` as INTEGER,
`hadm_id` as nullable INTEGER, `charttime` as `TIMESTAMP(0)`, and `valuenum`
as DOUBLE PRECISION. The full oracle manifest confirms the output types below.
There are no intermediate CTE columns.

| Output column | Source expression | Inferred/manifest type | Meaning of the SQL operation |
|---|---|---|---|
| `subject_id` | `MAX(subject_id)` | INTEGER | Maximum subject id among retained rows in the specimen group |
| `hadm_id` | `MAX(hadm_id)` | INTEGER, nullable | Maximum non-NULL hospital admission id in the group; `MAX` ignores NULL |
| `charttime` | `MAX(charttime)` | TIMESTAMP | Latest retained chart time in the specimen group |
| `specimen_id` | `le.specimen_id` | INTEGER | Grouping key, selected directly |
| `alt` | `MAX(CASE WHEN itemid = 50861 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained ALT value for the specimen |
| `alp` | `MAX(CASE WHEN itemid = 50863 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained ALP value for the specimen |
| `ast` | `MAX(CASE WHEN itemid = 50878 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained AST value for the specimen |
| `amylase` | `MAX(CASE WHEN itemid = 50867 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained amylase value for the specimen |
| `bilirubin_total` | `MAX(CASE WHEN itemid = 50885 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained total bilirubin value for the specimen |
| `bilirubin_direct` | `MAX(CASE WHEN itemid = 50883 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained direct bilirubin value for the specimen |
| `bilirubin_indirect` | `MAX(CASE WHEN itemid = 50884 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained indirect bilirubin value for the specimen |
| `ck_cpk` | `MAX(CASE WHEN itemid = 50910 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained CK/CPK value for the specimen |
| `ck_mb` | `MAX(CASE WHEN itemid = 50911 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained CK-MB value for the specimen |
| `ggt` | `MAX(CASE WHEN itemid = 50927 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained GGT value for the specimen |
| `ld_ldh` | `MAX(CASE WHEN itemid = 50954 THEN valuenum ELSE NULL END)` | DOUBLE | Maximum retained LD/LDH value for the specimen |

Referenced source columns, including non-output filter/group columns, are:
`subject_id`, `hadm_id`, `charttime`, `specimen_id`, `itemid`, and `valuenum`.
No other `labevents` column is selected or referenced.

## Filters

The single `WHERE` clause has three predicates:

1. `le.itemid IN (...)`, the exact literal set reproduced below.
2. `valuenum IS NOT NULL`.
3. `valuenum > 0`.

Thus zero and negative numeric values are excluded, as are NULL numeric values.
There is no time window, patient/admission restriction, text/value filter,
unit filter, flag/status filter, or code exclusion beyond membership in the
itemid set.

## Literal code set (verbatim)

This is the exact code set named by the canonical SQL. Every literal filters
`mimiciv_hosp.labevents.itemid` and feeds the indicated output CASE expression.
The comments are copied from the SQL and are descriptive source comments, not
replacement codes.

```sql
le.itemid IN
    (
        50861 -- Alanine transaminase (ALT)
        , 50863 -- Alkaline phosphatase (ALP)
        , 50878 -- Aspartate transaminase (AST)
        , 50867 -- Amylase
        , 50885 -- total bili
        , 50884 -- indirect bili
        , 50883 -- direct bili
        , 50910 -- ck_cpk
        , 50911 -- CK-MB
        , 50927 -- Gamma Glutamyltransferase (GGT)
        , 50954 -- ld_ldh
    )
```

Exact per-code feeds:

| `mimiciv_hosp.labevents.itemid` literal | Output column fed by the CASE |
|---:|---|
| `50861` | `alt` |
| `50863` | `alp` |
| `50878` | `ast` |
| `50867` | `amylase` |
| `50885` | `bilirubin_total` |
| `50883` | `bilirubin_direct` |
| `50884` | `bilirubin_indirect` |
| `50910` | `ck_cpk` |
| `50911` | `ck_mb` |
| `50927` | `ggt` |
| `50954` | `ld_ldh` |

There are no ICD codes, code versions, or other coded filters in this SQL.
No dead filter was identified from the source itself; all eleven itemid
literals must remain in the port specification even if a served-data probe
finds one absent.

## Grouping, aggregation, and natural-key implications

- `GROUP BY le.specimen_id` is the only grouping clause. There are no window
  functions or non-MAX aggregations.
- The oracle manifest identifies the comparison as `keyed_join` with natural
  key `["specimen_id"]` and reports 1,639,514 output rows.
- The result is one row per specimen, not one row per labevent, itemid, or
  patient/time pair. A specimen containing only a subset of the eleven codes
  still produces a row, with NULL for absent analyte columns (after the
  positive/non-NULL row filter).
- Every selected `MAX` is calculated independently over the retained rows.
  Therefore `subject_id`, `hadm_id`, and `charttime` are not guaranteed by the
  SQL to come from the same physical labevent row, and each analyte is the
  maximum value for its own itemid within the specimen. There is no tie-break
  or latest-value selection.
- `specimen_id` is non-NULL in the source DDL. `hadm_id` can remain NULL, and
  `MAX(hadm_id)` preserves NULL when all retained rows in a group have NULL
  admission id.

## FHIR-relevant mapping and caveats for the next agents

These are mapping facts and constraints for the prober/implementer, not a
ViewDefinition or SQL design.

- The relevant served stream is labevents-derived `Observation`. Its
  `Observation.code.coding.system` is
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`, and the code
  is the source itemid verbatim as a string. Filter by that system plus the
  exact eleven string codes before any integer cast; do not use
  `meta.profile` as the stream discriminator.
- The numeric source is `Observation.valueQuantity.value`, but the ETL can
  synthesize a Quantity from comparator text in `labevents.value` when source
  `valuenum` is NULL. Such comparator-derived values are not equivalent to the
  canonical `valuenum IS NOT NULL AND valuenum > 0` filter. The exact eleven
  itemids must be probed for this case; do not admit a Quantity solely because
  one exists, and preserve the strict positive numeric rule. Quantity aliases
  in materialized ViewDefinitions are string-like and require numeric typing
  before producing the DOUBLE output columns.
- `charttime` is carried by `Observation.effectiveDateTime`. The served lab
  ETL casts source charttime through `TIMESTAMPTZ`, so DST-gap times can be
  irreversibly shifted; the source analyst records this as a possible expected
  full-data conflict, not as a source filter. FHIR datetime strings should be
  handled as MIMIC wall-clock values with `TIMESTAMP_NTZ` semantics.
- `specimen_id` is not an Observation scalar. `Observation.specimen` resolves
  to a Specimen whose identifier has system
  `http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab` and whose string
  value is the relational `labevents.specimen_id`. This is the specimen
  grouping spine. Do not replace it with patient/time grouping.
- The Specimen ETL's `collection.collectedDateTime` is based on a MAX charttime
  over the specimen's labevents. The canonical enzyme `charttime` is the MAX
  only after restricting to the eleven itemids and positive, non-NULL
  `valuenum` rows. The prober must check whether those scopes coincide for the
  served enzyme item set; using Specimen collection time without that check
  can change the target.
- `subject_id` is recoverable from the referenced Patient's identifier value
  under the MIMIC patient identifier system; the value is a string and must be
  cast to INTEGER for this output shape. Resource UUID/reference keys are join
  keys, not the output id.
- `hadm_id` can be obtained only where the lab Observation has a hospital
  Encounter reference, whose identifier value is the hospital admission id.
  Lab Observation encounter references are incomplete. Preserve specimen rows
  with a LEFT join if an Encounter is used; an INNER join would turn a missing
  `hadm_id` into a missing output row. Patient-plus-time re-derivation is only
  a heuristic and must not manufacture an exact admission id. Expect a typed
  NULL candidate value where the oracle has a relational `hadm_id`.
- The source SQL has no FHIR terminology translation or ICD coding. The only
  coding system relevant to its filters is the proprietary MIMIC lab-item
  system above.

## Files checked

In addition to the canonical SQL and DAG entry, I checked
`mimic-iv/concepts_fhir/LOOP_CONTRACT.md`, the curated
`mimic-iv/concepts_fhir/MIMIC_NOTES.md`, and the relevant provisional fragments
`MIMIC_NOTES.d/README.md`, `chemistry.md`, `coagulation.md`,
`complete_blood_count.md`, `blood_differential.md`, and `cardiac_marker.md`.
The source DDL, full oracle manifest, and the labevents/specimen/encounter FHIR
ETL SQL were checked to ground the type, key, and FHIR caveats above. No
ViewDefinition or concept SQL was authored.
