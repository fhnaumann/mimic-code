# RESOLVED — no warehouse rebuild is needed

**Status:** closed 2026-08-13. The premise below was wrong: the warehouse was
never corrupted. Kept as the record of how that was established, because six
concepts still carry workarounds built against the wrong diagnosis.

**Outcome:** the "October family" was produced at **read time** by our own Spark
SQL under Petrichor's `Australia/Sydney` system zone. It is not in the data —
not upstream, and not in our copy.

---

## What was originally claimed

That the chartevents-derived `Observation` stream in
`/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse` carried **two**
independent DST spring-forward normalisations: the accepted upstream
`America/New_York` one (March, 2nd Sunday), plus an `Australia/Sydney` one
(October, 1st Sunday) introduced somewhere in our own materialisation.

The October dates were real observations, and they are all genuinely the first
Sunday in October — the Sydney spring-forward date. The inference that they were
therefore *stored* that way is what did not hold.

## What was measured

### 1. Our warehouse is bit-for-bit the upstream copy

All 13 Delta tables show the same history: an `UPDATE` (predicate over
`meta.profile`) followed by a `RESTORE` to version 0. The restore re-added the
original files and dropped the rewritten ones. Per table, the **active** file
set — reconstructed from the final commit, not from a directory listing —
equals the upstream set exactly:

| table | final op | active adds | vs `/datasets/…/mimic-iv-on-fhir-1.1.3_af91a8f/delta` |
|---|---|---|---|
| `Observation.parquet` | `RESTORE` | 3284 | identical set |
| other 12 tables | `RESTORE` | 1–262 | identical set |

Every one of the 3284 `Observation` files matches upstream on size; sampled
md5sums are identical. The 662 orphaned files from the reverted `UPDATE` are
still on disk and out of the table — that is the whole 126 GB vs 64 GB gap, and
a `VACUUM` reclaims it.

### 2. The column cannot be timezone-mangled at rest

`Observation.effectiveDateTime` is `BYTE_ARRAY` / `VARCHAR` — a literal
ISO-8601 string. No reader's session zone can alter it. The only offsets present
are `-04:00` and `-05:00`; there is no Sydney offset anywhere in the table.

### 3. The Sydney gap is fully populated; only the New York gap is empty

Census over the whole `Observation` table — upstream and ours, identical counts:

| day | 01:xx | 02:xx | 03:xx |
|---|---|---|---|
| March, 2nd Sunday (US DST start) | 27,474 | **0** | 66,707 |
| October, 1st Sunday (Sydney DST start) | 27,603 | **39,397** | 33,243 |
| all other days | 9,713,127 | 13,492,740 | 11,356,021 |

March 02:xx is empty with a doubled 03:xx bucket: the genuine upstream
`TIMESTAMPTZ` cast. October 02:xx holds 39,397 rows, so **no Sydney
normalisation was ever applied to the data**. One normalisation, not two.

## The actual root cause

Petrichor's system zone is `Australia/Sydney`, and `submit_concept_run.slurm`
did not set `spark.sql.session.timeZone` — so every full run inherited it. In
Spark 4.0.2, `DATE_FORMAT` and `DATE_TRUNC` consult the session zone **even for
a zone-less `TIMESTAMP_NTZ`**. Canary on the node, input
`2140-10-02T02:00:00-04:00`:

| expression on `TIMESTAMP_NTZ` | result |
|---|---|
| `CAST(… AS STRING)` | `02:00:00` ✅ |
| `DATE_FORMAT(…, 'yyyy-MM-dd HH:mm:ss')` | **`03:00:00`** ❌ |
| `DATE_TRUNC('HOUR', …)` | **`03:00:00`** ❌ |
| `TO_DATE(…)` | `2140-10-02` ✅ |

`2153-03-11 02:30` (a US gap, not a Sydney one) and a plain `2140-06-15 02:00`
are both untouched — the shift is DST-gap-specific, which is exactly the
signature that was mistaken for a second stored normalisation.

This confirms and generalises what `crrt` attempt_0002's
`evidence/mismatch-diagnostician.md` had already found for `DATE_FORMAT` alone.

## What was changed

1. `submit_concept_run.slurm` — `export TZ=UTC` plus
   `--conf spark.sql.session.timeZone=UTC`.
2. `oracle/submit_build_oracle.slurm` — `export TZ=UTC`.
3. `src/mimic_utils/embedded_runner.py` — `SESSION_TIMEZONE` (default `UTC`,
   overridable via `MIMIC_SPARK_TIMEZONE`) pinned at the single point where the
   JVM is created, so the local demo leg and the HPC leg cannot diverge. Pinning
   only the Slurm side would have made a Sydney laptop and a UTC compute node
   disagree — turning a config bug into a phantom port bug.
4. `.opencode/skills/csiro-hpc/SKILL.md` — the rule, the measurement, and both
   job templates.

`UTC` rather than `America/New_York` because UTC has no DST in any year, so no
wall clock can be normalised by accident. The original worry that this "changes
what the six concepts should be compared against" does **not** apply: nothing is
being rebuilt, the stored strings are unchanged, and the upstream March shifts
are already baked into them.

## What is still open

- **The six concepts' workarounds are half-obsolete.** `icp`, `gcs`, `height`,
  `crrt`, `icustay_times` reverse-engineer the `Observation.id` UUIDv5 to undo a
  one-hour shift; `code_status` does it with nine hardcoded UUID literals. The
  **March** half is real and stays — that shift genuinely is in the data. The
  **October** half was compensating for a defect that never existed and should
  come out. Whether the recorded October residuals clear completely under a
  pinned zone needs a rerun, not more inspection.
- **`gcs` does not unblock here regardless.** It also uses the UUID witness to
  recover the source label `No Response-ETT`, which the ETL discards when it
  writes `valueQuantity`. That is essential representation loss: it changes
  three outputs and temporal carry-forward, so the whole concept must go to the
  judge for `BLOCKED_REPRESENTATION`, not a column declaration. See
  `TODO_reopen_uuid_inversion.md`.
- **The upstream issue stands.** The March family is genuinely `mimic-fhir`'s
  (`fhir_encounter.sql:65`, `fhir_observation_chartevents.sql:67`) and remains
  an accepted, attributed divergence. The October family was never theirs and
  the issue should not claim it.
- **No `sql_lint.py` rule was added, deliberately.** `DATE_FORMAT` and sub-day
  `DATE_TRUNC` on a `TIMESTAMP_NTZ` are the same class as the cast rules the
  linter already gates, and a rule was drafted and measured against the corpus
  (2 true hits, both `crrt/attempt_0002`; 0 false positives on the 23 frozen
  artifacts). It was dropped because **pinning the zone removes the defect
  rather than detecting it**: UTC has no DST in any year, so there is no gap for
  those functions to normalise into, and `embedded_runner` is the only Spark
  entry point in the codebase — `demo_runner` and `cast_probe` both route
  through it, and `hpc.py` never creates a context. A lint rule here would gate
  a construction that is now harmless. Revisit only if the pin is ever removed.
- **662 orphaned `Observation` files** (~62 GB) are recoverable with a `VACUUM`.
