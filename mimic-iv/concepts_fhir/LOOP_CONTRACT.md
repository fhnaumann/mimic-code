# Loop contract — MIMIC-IV → MIMIC-on-FHIR concept port

Authoritative statement of what the loop compares, where, and what gates what.
Where this file and any agent prompt, skill, or README disagree, **this file wins**
and the other document is a bug.

Decided 2026-08-05.

## What is being claimed

For one named derived concept, two *different* queries must produce the *same table*:

- **Oracle** — the canonical MIMIC-IV SQL (`mimic-iv/concepts/`), run over relational
  MIMIC-IV 2.2.
- **Candidate** — a FHIR ViewDefinition + SQL authored by the agent, run over
  MIMIC-on-FHIR 2.1 through Pathling.

The port is not "the same query on two datasets". There is no `admissions` table in
FHIR. It is two unrelated queries whose output tables must agree, which is why the
comparison *is* the experimental claim rather than a smoke test attached to one.

## The oracle is computed once

| | |
|---|---|
| Path | `/scratch3/nau025/oracle/mimic4-full.db` (HPC, Lustre) |
| Contents | 22 `mimiciv_hosp`, 9 `mimiciv_icu`, 65 `mimiciv_derived` tables |
| Derived rows | 72,221,096 |
| Engine | DuckDB 1.5.5 |
| Built by | `mimic_utils.build_full_oracle` |
| Contract | `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` |

Immutable. The loop never recomputes it. Rebuild only if the concept SQL baseline
moves off commit `3a914fc`, and then regenerate the manifest in the same pass.

The manifest is the artifact that travels to the laptop: per concept, the exact row
count, columns and types, the natural key, and an order-independent content hash.
An agent reads the manifest to learn the target shape without touching the 14.5 GB
oracle.

## Comparison method

Keyed row-level diff, executed as DuckDB SQL. Never materialise rows into Python —
`vitalsign` alone is 9.7M rows.

- **52 concepts** have an empirically-unique key → full outer join on that key,
  then per-column value comparison. Reports rows only-in-oracle, only-in-candidate,
  matched-but-differing (**and which column** differs), and identical.
- **13 concepts** have no unique key within 3 columns → full-tuple multiset
  comparison. Complete, but names no column, so it is less diagnostic.

Keys are discovered **empirically against full data**, never parsed from SQL and
never derived from demo. Two rules, both learned the hard way:

1. A key must be **anchored** by at least one identity column. On 100 demo patients
   a bare `charttime` is unique; at 300k patients it is not.
2. Demo-derived keys are unsafe. Nine of 65 disagree with full data, and for `bg`,
   `kdigo_creatinine`, `kdigo_stages` and `phenylephrine` the demo key is **not
   unique** on full data — a join on it would silently fan out.

Prefer the **smallest** unique key. If a port gets `subject_id` wrong but `hadm_id`
right, keying on `hadm_id` alone reports a value mismatch in a named column; keying
on both reports "row missing" plus "extra row", which localises nothing.

## Gates

### Demo — cheap shape gate, NOT a correctness gate

Runs locally: Pathling over the demo Delta warehouse, seconds per attempt, no queue.
Its job is to catch the errors that do not need 156 GB to reveal:

- the ViewDefinition or SQL fails to execute at all
- returned column **names** do not match the target
- returned column **types** are incompatible
- output shape is structurally wrong

Explicitly **not** a demo gate:

- **Row count is not a demo gate.** Demo agreement is not evidence of correctness and
  demo disagreement is not proof of a bug.
- **0 rows on demo is `unsure`, never `fail`.** The 100-patient cohort legitimately
  contains nothing for some concepts. Do not fail, and do not pass — proceed to full.

A demo failure is a fast, cheap bug report. A demo pass earns nothing except
permission to spend an HPC run.

### Full data — the real correctness signal, inside the loop

Runs on HPC: Pathling/Spark over the 156 GB `spark_warehouse`, compared against the
oracle in the same job (both node-local, no data movement). ~10–30 min per run plus
queue.

- This is where correctness is decided: exact row count, schema, and the keyed diff.
- The agent may submit **as many full runs as it judges necessary**, iterating on the
  diff each time.
- **Hard cap: 10 full runs per concept.** On the 10th without convergence the concept
  terminates for human review.

The full run is *not* a final one-shot confirmation of a demo-approved answer. Demo
never approves an answer; it only rejects malformed ones.

## Terminal states

| State | Reached when |
|---|---|
| `COMPLETED` | full-data hard gates pass |
| `BLOCKED_REPRESENTATION` | judge confirms an intrinsic FHIR gap, citing a specific element or path |
| `FAILED` | 10 full runs without convergence, or an unrecoverable error |

A judge-confirmed representability gap is a documented blocked state, not a pass.
The judge assesses representability only; it can never override a hard gate.

## Data locations

| | |
|---|---|
| Full oracle | `/scratch3/nau025/oracle/mimic4-full.db` (HPC) |
| Full FHIR | `/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse` (HPC, 156 GB) |
| Demo oracle | `/Users/nau025/warehouses/mimic4-demo.db` (local, read-only) |
| Demo FHIR | `/Users/nau025/warehouses/mimic-iv-demo/delta` via Pathling `localhost:8080` |
| Terminology | `https://velonto.dw.csiro.au/fhir` (ConceptMaps authoritative) |

Every code path opens a DuckDB oracle with `read_only=True`.
