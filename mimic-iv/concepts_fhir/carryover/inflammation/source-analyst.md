# Source analysis: inflammation

## Source and DAG identity

- Concept: `inflammation`
- Canonical SQL: `mimic-iv/concepts/measurement/inflammation.sql`
- DAG path: `measurement/inflammation.sql`
- DAG level: `0`
- DAG SQL SHA256: `88b7cc933d2832aed284a489ee67a3a156e67365c96e60706fb6eb6c537590c9`
- DAG dependencies: none
- DAG dependents: none
- The DAG therefore requires no `mimiciv_derived` concept to be ported first.

## Query shape and exact semantics

The SQL is one aggregate query with no CTEs, subqueries, `DISTINCT`, or `ORDER BY`.
It selects from qualifying CRP laboratory rows and groups them by `specimen_id`.
For each specimen group, it independently takes the maximum subject ID, admission
ID, chart time, and numeric CRP value. The `MAX` values for subject/admission/time
are independent aggregates; they are not guaranteed to come from the same source
row. Because the executable item filter admits only item `50889`, `crp` is the
maximum positive, non-null `valuenum` for item `50889` within each specimen.

The result has one row per qualifying `specimen_id`. `specimen_id` is the natural
key. The full-data oracle manifest records 117,898 rows and the following output
types: `subject_id INTEGER`, `hadm_id INTEGER`, `charttime TIMESTAMP`,
`specimen_id INTEGER`, and `crp DOUBLE`.

## Table references

| SQL clause | Source qualification | Schema | Table | Alias | Join type/condition |
|---|---|---|---|---|---|
| `FROM` | ``physionet-data.mimiciv_hosp.labevents le`` | `mimiciv_hosp` | `labevents` | `le` | Base table; no join |

There are no `JOIN` clauses and no references to `mimiciv_derived`.

## Columns and inferred types

The canonical labevents DDL gives `subject_id INTEGER NOT NULL`, `hadm_id INTEGER`
(nullable), `specimen_id INTEGER NOT NULL`, `itemid INTEGER NOT NULL`,
`charttime TIMESTAMP(0)`, and `valuenum DOUBLE PRECISION`. The SQL references the
following columns:

| Source column | Type in source context | Use | Output |
|---|---|---|---|
| `le.subject_id` | `INTEGER` | `MAX(subject_id)` | `subject_id` (`INTEGER`) |
| `le.hadm_id` | nullable `INTEGER` | `MAX(hadm_id)` | `hadm_id` (`INTEGER`, nullable when all group values are NULL) |
| `le.charttime` | `TIMESTAMP(0)` | `MAX(charttime)` | `charttime` (`TIMESTAMP`) |
| `le.specimen_id` | `INTEGER` | `GROUP BY` and selected directly | `specimen_id` (`INTEGER`), natural key |
| `le.itemid` | `INTEGER` | executable `IN` filter and conditional `CASE` predicate | Determines rows contributing to `crp`; not output directly |
| `le.valuenum` | `DOUBLE PRECISION` | `IS NOT NULL`, `> 0`, and conditional aggregate input | `crp` (`DOUBLE`) |

There are no intermediate CTE columns. The output aliases are exactly:
`subject_id`, `hadm_id`, `charttime`, `specimen_id`, and `crp`.

## Filters

The complete executable `WHERE` predicate is:

1. `le.itemid IN (50889)`. The SQL contains a commented-out `51652` line in the
   `IN` list, but it is not executable and does not admit rows.
2. `valuenum IS NOT NULL`.
3. `valuenum > 0`.

There is no time window, admission window, unit filter, text/value filter, code
exclusion, or additional null predicate. The positive constraint excludes zero
and negative numeric results. Since `50889` is the only active item, every output
group has at least one positive, non-null CRP input and `crp` is non-null.

## Literal code specification

The code set below is copied from the SQL and distinguishes executable literals
from the commented literal. Do not expand, translate, or substitute labels.

| Source table filtered | Source column / coding | Exact literal as written | Status | Output/CTE fed |
|---|---|---:|---|---|
| `mimiciv_hosp.labevents` | `itemid` | `50889` | **Executable** (`-- crp`) | `crp` through `MAX(CASE WHEN itemid = 50889 THEN valuenum ELSE NULL END)` |
| `mimiciv_hosp.labevents` | `itemid` | `51652` | **Commented out**, not part of the executable filter (`-- 51652 -- high sensitivity CRP`) | None; if uncommented, it would pass the `IN` predicate but the `CASE` has no `51652` branch, so it would produce a group with `crp = NULL` unless the CASE were also changed |

For the FHIR-side itemid-derived lab Observation stream, the relevant coding
system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`, and the
code is the unchanged string `50889`. The source SQL names no ICD or other code
system.

## Aggregations and grouping

- `GROUP BY le.specimen_id` is the only grouping operation.
- `MAX(subject_id)` produces `subject_id`.
- `MAX(hadm_id)` produces `hadm_id` and remains NULL if every group value is NULL.
- `MAX(charttime)` produces `charttime`; SQL `MAX` ignores NULLs and returns NULL
  only when all group chart times are NULL.
- `MAX(CASE WHEN itemid = 50889 THEN valuenum ELSE NULL END)` produces `crp`.
- There are no window functions, `MIN`, `AVG`, `SUM`, array aggregations, or
  other value aggregations.

## Port-relevant dataset/IG quirks

The following cross-concept findings are relevant to reproducing this source
shape; they describe data representation, not clinical interpretation:

1. **Specimen is the lab grouping spine.** Lab Observations reference a
   `Specimen`, whose `identifier` with system
   `http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab` preserves the
   relational `labevents.specimen_id` as a string. Grouping by patient and time
   instead of this specimen identifier would not preserve the SQL's grouping.
2. **The lab Observation encounter reference is incomplete.** The source
   `hadm_id` is populated in relational labevents, but FHIR lab
   `Observation.encounter` is not guaranteed. If an Encounter lookup is used to
   recover `hadm_id`, it must be a LEFT-join strategy rather than an INNER join;
   the dataset-wide notes state that no exact FHIR path recovers missing
   relational `hadm_id`, so a missing candidate `hadm_id` is an expected
   representability gap rather than permission to invent an admission ID.
3. **Itemids are verbatim FHIR codes.** For labevents, the FHIR code is
   `CAST(itemid AS TEXT)` under the `mimic-d-labitems` system; `d_labitems` is
   used for display only. MIMIC-IV 2.2's `d_labitems` has no relational LOINC
   columns, so do not replace `50889` with a LOINC code.
4. **Numeric-value filtering must distinguish source numeric values.** The
   labevents ETL can synthesize a FHIR Quantity from comparator text when source
   `valuenum` is NULL, and can use comments as a `valueString` fallback. The
   source predicate is specifically `valuenum IS NOT NULL AND valuenum > 0`; a
   FHIR port must not admit comparator-derived or comments-derived values as if
   they were source `valuenum` rows.
5. **Datetime representation is lossy and offset-bearing.** Lab effective times
   and lab specimen collection times are serialized through the FHIR ETL's
   timezone behavior. A downstream port should preserve the MIMIC wall-clock
   value with `TIMESTAMP_NTZ`-style handling, not offset-normalize it locally.
   DST-gap source times can already have been irreversibly shifted by the ETL;
   this may affect exact `charttime` comparison and, in general, time-based
   reconstruction. This concept's SQL itself has no time filter.
6. **Observation subtype metadata is not a safe discriminator.** If filtering
   the served Observation table, use the base coding system plus exact code,
   rather than relying on `meta.profile`, because warehouse variants differ in
   subtype profile metadata.

No dataset-wide quirk in the reviewed notes changes the source code set or the
SQL's one-row-per-specimen aggregate semantics. The lab specimen spine,
incomplete encounter/hadm representation, numeric-value ETL branches, verbatim
itemid coding, and datetime behavior are relevant constraints for the eventual
FHIR mapping.

## Files and evidence basis

Read and checked:

- `AGENTS.md`
- `mimic-iv/concepts/measurement/inflammation.sql`
- `mimic-iv/concept_dag/concept_dag.json`
- `mimic-iv/concepts_fhir/LOOP_CONTRACT.md`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.md`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/README.md`
- All existing fragments under `mimic-iv/concepts_fhir/MIMIC_NOTES.d/`: `arb.md`,
  `blood_differential.md`, `cardiac_marker.md`, `chemistry.md`,
  `code_status.md`, `coagulation.md`, `complete_blood_count.md`, `crrt.md`,
  `dobutamine.md`, `dopamine.md`, `epinephrine.md`, `gcs.md`, `height.md`,
  `icp.md`, and `icustay_detail.md`.
- `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` (the inflammation
  schema, key, and row-count entry)
- `mimic-iv/buildmimic/postgres/create.sql` (the labevents column definitions)
- `mimic-iv/concepts_fhir/carryover/README.md` (carryover protocol)

Produced:

- `mimic-iv/concepts_fhir/carryover/inflammation/source-analyst.md`
