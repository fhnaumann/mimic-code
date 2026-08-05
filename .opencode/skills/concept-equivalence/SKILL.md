---
name: concept-equivalence
description: Run the deterministic comparator for a MIMIC-IV to MIMIC-on-FHIR concept port. Two strengths — demo is a cheap SHAPE gate only (execution, column names, types; row count NOT gated, 0 rows means unsure), full data is the correctness gate (exact row count, schema, keyed row-level diff against the immutable full oracle). Hard gate failures produce mismatch; the judge cannot override them. Trigger phrases include "compare concepts", "equivalence", "comparator", "keyed diff", "row count match".
---

# concept-equivalence

The deterministic comparator for a MIMIC-IV → MIMIC-on-FHIR concept port.

`mimic-iv/concepts_fhir/LOOP_CONTRACT.md` is authoritative on gate semantics;
this skill implements it. If they disagree, the contract wins.

## What is being compared

Two *different* queries must produce the *same table*: the canonical MIMIC-IV
SQL over relational MIMIC-IV, and an agent-authored FHIR ViewDefinition + SQL
over MIMIC-on-FHIR. There is no shared query — the comparison **is** the
experimental claim, not a smoke test bolted onto one.

The oracle side is **already computed** and immutable:

| | |
|---|---|
| Full oracle | `/scratch3/nau025/oracle/mimic4-full.db` (HPC, read-only) |
| Contract | `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` |
| Derived rows | 72,221,096 across 65 concepts |

Never recompute the oracle. Read its shape from the manifest: per concept, the
exact `row_count`, `columns` (names + types), `key`, and `content_hash`.

## Two gates, different strengths

### Demo — shape only, NOT correctness

Local Pathling, seconds, no queue. Its entire job is to stop a malformed port
from consuming a 10–30 minute HPC run.

Gated:
- **Execution** — the ViewDefinition and SQL run at all.
- **Column names** — case-sensitive exact match against the manifest. Order
  does not matter.
- **Column types** — compatible (FLOAT vs DOUBLE matches; INTEGER vs STRING
  does not). DuckDB and Spark/Pathling type names are normalized.

**Not** gated:
- **Row count.** Report it as an observation. Demo agreement is not evidence of
  correctness, and demo disagreement on count is not proof of a bug.
- **0 rows ⇒ `unsure`, never `fail`.** The 100-patient cohort legitimately
  holds nothing for some concepts — `neuroblock` has 0 demo rows and 14,174 on
  full data. Proceed to full data.

### Full data — correctness

On HPC, against the immutable oracle, both sides node-local. Hard gates:

1. **Row count identity** — exact. No tolerance. Floating-point tolerances
   apply only to per-column value comparisons, never to row count.
2. **Column schema identity** — same names, compatible types.
3. **Keyed row-level diff** — see below.

## The keyed diff

Computed as **SQL inside DuckDB**. Never materialise rows into Python:
`vitalsign` is 9.7M rows and `rhythm` is 5.9M.

52 of 65 concepts have an empirically-unique key in the manifest. Join on it:

```sql
SELECT
  count(*) FILTER (WHERE c.<key> IS NULL)                        AS only_oracle,
  count(*) FILTER (WHERE o.<key> IS NULL)                        AS only_candidate,
  count(*) FILTER (WHERE o.<key> IS NOT NULL
                     AND c.<key> IS NOT NULL AND NOT <all_cols_equal>) AS differing,
  count(*) FILTER (WHERE o.<key> IS NOT NULL
                     AND c.<key> IS NOT NULL AND <all_cols_equal>)     AS identical
FROM oracle.mimiciv_derived."<concept>" o
FULL OUTER JOIN read_parquet('<candidate>.parquet') c USING (<key cols>)
```

Then a per-column tally of which columns differ among the `differing` rows.
That is what makes a diagnosis possible: "`age` differs on 1,204 rows" is
actionable, "counts differ" is not.

The remaining 13 concepts have no unique key within 3 columns and are compared
as **full-tuple multisets** — complete, but it names no column, so diagnosis is
harder. Those concepts are listed in the manifest with
`"comparison": "full_tuple_multiset"`.

### Why not min/max

Per-column min/max identity is **not** evidence of equivalence. A port that
computes every value correctly but attaches it to the wrong key satisfies min,
max, row count, and schema simultaneously. Prefer the smallest unique key for
the same reason: if a port gets `subject_id` wrong but `hadm_id` right, keying
on `hadm_id` alone reports a value mismatch **in a named column**, whereas
keying on both reports "row missing" plus "extra row" and localises nothing.

## Invocation

```bash
mimic_utils compare-port-results ORIGINAL CANDIDATE --output comparison.json
```

Never hand-calculate a verdict. The comparator output is a small JSON artifact
— counts per category, a per-column mismatch tally, and a bounded sample of
each mismatch class — small enough to travel back from HPC and be stored in
the attempt directory.

## Tolerance (values only, never row count)

```python
def within_tolerance(a, b, rel_tol=0.001, abs_tol=1e-6):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
```

Timestamps compare within 1 second. Strings and integers compare exactly.

## Verdicts

| Verdict | Meaning |
|---|---|
| `shape_ok` | demo only: executed, names and types match. Earns permission to spend an HPC run — nothing more. |
| `unsure` | demo only: executed, shape fine, 0 rows. Proceed to full data. Never a failure. |
| `match` | **full data only**: every hard gate passes. Permits `mimic_utils done <concept>`. |
| `mismatch` | one or more hard gates fail. The mismatch diagnostician must be invoked. The judge CANNOT override it. |

A demo result never yields `match` and never permits `done`. Correctness is
decided only on full data, which may be run as many times as needed up to the
hard cap of 10 per concept.
