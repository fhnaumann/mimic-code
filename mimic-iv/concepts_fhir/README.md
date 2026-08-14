# MIMIC-on-FHIR Derived Concepts

This directory stores write-once attempts to reproduce the canonical
MIMIC-IV derived concepts on MIMIC-on-FHIR.

## Layout

```text
concepts_fhir/
  LOOP_CONTRACT.md                  # authoritative gate semantics
  MIMIC_NOTES.md                    # shared dataset/IG quirks — curated, read-only to a loop
  MIMIC_NOTES.d/<concept>.md        # append-only findings fragment, one per concept
  config.json
  oracle/
    oracle_manifest.full.json       # per-concept row count, columns, key, hash
    submit_build_oracle.slurm
  state/<concept>/state.json
  metrics/<concept>/run_NNNN.json      # write-once conversion usage/outcome metrics
  concepts/<category>/<concept>/attempt_NNNN/
    ViewDefinition*.json
    concept.sql
    shape.demo.json                 # demo shape-gate result
    comparison.full.json            # full-data keyed diff (the real verdict)
    hpc_accounting.json             # final Slurm elapsed runtime from sacct
    evidence/<stage>.md
```

`mimic_utils start <concept>` creates the next attempt directory. Each
artifact may be created once; existing attempt artifacts are never edited or
replaced. A correction requires `mimic_utils fail` followed by
`mimic_utils retry`, which creates a new attempt.

`MIMIC_NOTES.md` is the loop's curated record of MIMIC-on-FHIR dataset and IG
quirks that hold regardless of concept. Agents read it before probing or
authoring SQL, but they do not write to it: findings are appended to
`MIMIC_NOTES.d/<concept>.md`, one fragment per concept, so parallel goals never
contend over a shared file. A human merges the fragments in between waves,
which is what makes an entry in `MIMIC_NOTES.md` mean "checked" and a fragment
mean "one loop currently believes" — protocol in `MIMIC_NOTES.d/README.md` and
`AGENTS.md` → "Shared dataset knowledge".

## Lifecycle

```text
PENDING -> RUNNING -> VALIDATING_DEMO -> VALIDATING_FULL -> COMPLETED
                                                        \-> COMPLETED_WITH_DIVERGENCE
                     \-> BLOCKED_REPRESENTATION (human review)
```

**Both legs execute on Spark**, via embedded Pathling over a Delta warehouse:
the demo warehouse locally, the 156 GB warehouse on the HPC. The full leg has no
alternative — compute nodes have no FHIR server — so the demo leg matches it
deliberately, and a demo failure therefore predicts a full-run failure. There is
no HTTP Pathling server anywhere in the loop, and no second execution path.

Before a target concept's SQL runs, the executor preprocesses each completed
`mimiciv_derived` dependency in DAG order and registers its candidate output as a
Spark temp view named by the dependency stem. A dependent SQL query therefore
uses `FROM age` just as the canonical query uses `FROM mimiciv_derived.age`;
agents must not inline or rederive a dependency. The HPC launcher stages the
same dependency attempts for the full-data leg.

Both legs write **Parquet**, so the comparator reads the Spark schema rather
than re-inferring types from serialised text. That distinction is not cosmetic:
an all-null column (legitimate whenever a concept's shape needs a column
MIMIC-on-FHIR cannot populate) infers as `JSON` from NDJSON and fails a
`SMALLINT` expectation for reasons that have nothing to do with the port.

The two comparators have **different strengths** — see `LOOP_CONTRACT.md`,
which is authoritative:

- **Demo (`VALIDATING_DEMO`) is a cheap shape gate, not a correctness gate.**
  It rejects a port that fails to execute or returns wrong column names/types.
  Row count is **not** gated, and **0 rows is `unsure`, never `fail`**. A demo
  pass earns nothing but permission to spend an HPC run.
- **Full data (`VALIDATING_FULL`) decides correctness**: schema identity, and a
  keyed row-level diff against the immutable full oracle that *classifies* every
  divergence. It may run **as many times as needed, capped at 10 per concept**;
  it is not a one-shot confirmation of a demo-approved answer.

**Row count is not a hard gate.** MIMIC-on-FHIR does not carry everything
relational MIMIC-IV carries, so a faithful port can legitimately return fewer
rows. What decides the verdict is the *kind* of divergence:

| Verdict | Reached when | Terminal state |
|---|---|---|
| `match` | nothing diverged | `COMPLETED` |
| `mismatch` | schema failed, or the candidate invented rows / conflicts on values — neither of which a coverage gap can cause | back to the diagnostician; `FAILED` at the cap |
| `review` | only missing rows or candidate NULLs remain — the shape of a real coverage gap | the judge decides: `COMPLETED_WITH_DIVERGENCE` or back to the loop |

`COMPLETED` and `COMPLETED_WITH_DIVERGENCE` are **reported separately and never
summed** — "N exact, M accepted with documented divergence" is a claim the
artifacts support, "N+M completed" is not. An accepted divergence requires the
judge's cited justification, recorded via
`mimic_utils accept-divergence <concept> --justification "..."`.

Reaching the 10-run cap terminates for human review.

## Result Artifact

Both runners write Parquet — `candidate.demo.parquet` and
`candidate.full.parquet` — as a directory of Spark part-files, addressed by a
`.../*.parquet` glob. DuckDB scans them natively, so rows are never
materialised into Python (`vitalsign` is 9.7M rows) and the Spark schema
reaches the comparator intact.

Nothing about the demo artifact is a scaled-down variant of the full one: same
writer, same format, same scan path, same comparator. The only difference is
which warehouse produced it and which comparison mode reads it.

DuckDB and Spark/Pathling type names are normalized by
`mimic_utils compare-port-results`. Numeric tolerance applies only to
floating-point values, never to counts — and row count is reported rather than
gated (see the lifecycle table above).

## Configuration

`config.json` records stable dataset and service identities. Runtime secrets
and machine-specific credentials belong in environment variables or the
referenced external pipeline configuration, never in this directory.

### `MIMIC_SPARK_LOCK` — the local Spark lease

Set it to a lockfile path before running waves of parallel goals:

```bash
export MIMIC_SPARK_LOCK="$HOME/.mimic-spark.lock"
```

The embedded executor takes an exclusive `flock` on that file before starting
the JVM and holds it until the session stops, so at most one local Spark runs
at a time however many goals are in flight. Without it, parallel demo runs
share one driver heap and collide on the repo-root `spark-warehouse/` Derby
metastore. A blocked run waits up to 60 minutes and logs how long it waited
(`spark lease acquired after 214s`); the pid written into the file is
diagnostics, not the mechanism. Unset the variable and there is no locking at
all — which is exactly how the HPC job runs, since the Slurm script never sets
it and Lustre should not be asked for an `flock`.
