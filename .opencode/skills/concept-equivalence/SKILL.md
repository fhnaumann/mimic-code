---
name: concept-equivalence
description: Run the deterministic comparator for a MIMIC-IV to MIMIC-on-FHIR concept port. Two strengths — demo is a cheap SHAPE gate only (execution, column names, types; row count NOT gated, 0 rows means unsure), full data is the correctness gate (schema identity plus a keyed row-level diff against the immutable full oracle). Row count is NOT a hard gate on either leg, and neither is a value conflict; the full diff classifies divergence and returns match / mismatch / review. `mismatch` is reserved for machine-provable contradictions (execution, schema, a self-refuting unrepresentable declaration) and the judge is not called. Everything else routes to the judge carrying a tier: `gap_shaped` (missing rows, candidate NULLs) or `contested` (conflicting values, invented rows), which needs an upstream ETL citation to accept. Trigger phrases include "compare concepts", "equivalence", "comparator", "keyed diff", "row count match", "divergence".
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

On HPC, against the immutable oracle, both sides node-local.

1. **Column schema identity** — same names, compatible types. **Hard gate.**
2. **Keyed row-level diff** — see below. Which divergence *classes* it finds
   decides the verdict.
3. **Row count** — reported, **never gated**. MIMIC-on-FHIR does not carry
   everything relational MIMIC-IV carries, so a faithful port can legitimately
   return fewer rows.

## The keyed diff

Computed as **SQL inside DuckDB**. Never materialise rows into Python:
`vitalsign` is 9.7M rows and `rhythm` is 5.9M.

52 of 65 concepts have an empirically-unique key in the manifest. Join on it,
and split key-matched rows three ways rather than two:

```sql
SELECT
  count(*) FILTER (WHERE c.<key> IS NULL)              AS only_oracle,
  count(*) FILTER (WHERE o.<key> IS NULL)              AS only_candidate,
  count(*) FILTER (WHERE <both> AND <any_conflict>)    AS differing_conflict,
  count(*) FILTER (WHERE <both> AND NOT <any_conflict>
                     AND <any_candidate_null>)         AS differing_null_only,
  count(*) FILTER (WHERE <both> AND <all_cols_equal>)  AS identical
FROM oracle.mimiciv_derived."<concept>" o
FULL OUTER JOIN read_parquet('<candidate>.parquet') c USING (<key cols>)
```

where, per column, `candidate_null` is `o.col IS NOT NULL AND c.col IS NULL`
and `conflict` is everything else that is not equal — both sides holding
disagreeing values, or the candidate holding a value where the oracle is NULL.
A row is classified by its worst column: one conflict makes the whole row a
conflict.

Plus a per-column tally for each class, so a diagnosis can say "`age` conflicts
on 1,204 rows" or "`dose_due` is NULL on 8,900 rows" instead of "counts differ".

### Why the split decides the verdict

`differing` on its own conflates a divergence the judge may forgive with one it
may not:

| Class | Can a coverage gap cause it? | Tier |
|---|---|---|
| `only_oracle` | yes — this is what a gap looks like | `gap_shaped` |
| `differing_null_only` | yes — the FHIR element does not exist | `gap_shaped` |
| `only_candidate` | no — fan-out, a wrong filter, or an upstream row | `contested` |
| `differing_conflict` | no — the row exists on both sides | `contested` |

- `match` — nothing diverged. The judge is never called.
- `mismatch` — a machine-provable contradiction: the candidate did not execute,
  the schema is wrong, or a declared-unrepresentable column holds values. The
  judge is not called; there is nothing to weigh.
- `review` — everything else, carrying `divergence.tier` and
  `divergence.judge_bar`. The judge decides. There is no size threshold; a
  divergence of any magnitude reaches it, and none is auto-accepted.

**A value conflict is `contested`, not a failure.** MIMIC-on-FHIR is a
*transform* of MIMIC-IV, not a subset: `fhir_patient.sql:15` synthesises
`birthDate` from `MIN(transfers.intime)`, `fhir_encounter.sql:65` DST-shifts
admission times. Those produce conflicts no port can invert, and they are
shape-identical to a port bug — so the comparator names the shape and the judge
decides which, at a bar that requires citing the upstream ETL statement.
A conflict outranks a gap: a result with both is `contested`.

Exit codes follow: **0** `match`, **1** `mismatch`, **2** `review` at either
tier (and **2** for a demo `unsure`). A caller that treats any non-zero exit as
failure will turn "the judge must look at this" into "this port is wrong" —
most likely on `contested`, which reads as serious.

The remaining 13 concepts have no unique key within 3 columns and are compared
as **full-tuple multisets** — complete, but it names no column, so diagnosis is
harder. Those concepts are listed in the manifest with
`"comparison": "full_tuple_multiset"`.

They also cannot be classified: with no key to align rows, a row whose only
fault is a NULL lands in `only_oracle` **and** `only_candidate` at once,
indistinguishable from an invented row. Their results carry
`classification: "unavailable_no_key"`, and their `only_candidate` count is
ambiguous in a third way on top of the two every conflict already carries. The
judge is told it is reasoning with less evidence, and should treat
`only_candidate` there as a bug unless the evidence positively shows otherwise.

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
| `match` | **full data only**: nothing diverged. Permits `mimic_utils done <concept>`. |
| `mismatch` | **full data only**: a machine-provable contradiction — execution, schema, or a declaration the data refutes. The diagnostician must be invoked. The judge is not called. |
| `review` | **full data only**: divergence the judge decides. Tier `gap_shaped` needs a named absent FHIR element; tier `contested` needs the upstream ETL statement that rewrote the value. Never a failure. |

A demo result never yields `match` and never permits `done`. Correctness is
decided only on full data, which may be run as many times as needed up to the
hard cap of 10 per concept.
