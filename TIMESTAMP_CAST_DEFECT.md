# Timestamp-cast defect — working notes

Scratch file. Not part of the loop's artifacts. Delete when the sweep is done.

Scanned 2026-08-11 against each concept's **current** attempt `concept.sql`.

## The rule being violated

`MIMIC_NOTES.md:337` — "FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ,
never to TIMESTAMP". Use `CAST(col AS TIMESTAMP_NTZ)` / `TRY_CAST`, with nothing
wrapped around it. Now also stated as a negative rule in
`.opencode/skills/pathling-sql/SKILL.md`, which is where the agents were getting
away with the hedge.

## The two constructions

### A — COALESCE fallback to an offset-aware parser

```sql
COALESCE(
    TRY_CAST(effective_text AS TIMESTAMP_NTZ),
    CAST(TRY_TO_TIMESTAMP(effective_text, "yyyy-MM-dd'T'HH:mm:ssXXX") AS TIMESTAMP_NTZ)
)
```

The fallback re-renders the instant in `spark.sql.session.timeZone`. Measured
0/275 against the oracle at `Australia/Sydney` and `UTC`, 275/275 only at
`America/New_York`. It is live exactly when `TRY_CAST` returns NULL — the least
observable case — and demo (laptop) vs full (Petrichor) can disagree.

### B — regex-strip + pinned format

```sql
CAST(
    TRY_TO_TIMESTAMP(
        REGEXP_REPLACE(starttime_str, '(Z|[+-][0-9]{2}:[0-9]{2})$', ''),
        "yyyy-MM-dd'T'HH:mm:ss[.SSSSSS]"
    ) AS TIMESTAMP_NTZ
)
```

Returns NULL on any shape the pinned format misses — date-only values especially
— and `TRY_` makes that silent. Those NULLs land in `differing_null_only`, which
tiers as `gap_shaped`: **the port's own parse failure reaches the judge disguised
as a FHIR coverage gap, at the lower evidentiary bar.** This is the one that gets
accepted.

### Correct

```sql
TRY_CAST(effective_text AS TIMESTAMP_NTZ)
```

## Affected

| Concept | Att | State | Defect |
|---|---|---|---|
| acei | 4 | COMPLETED_WITH_DIVERGENCE | B |
| antibiotic | 1 | COMPLETED_WITH_DIVERGENCE | B |
| arb | 2 | COMPLETED_WITH_DIVERGENCE | B |
| cardiac_marker | 2 | COMPLETED_WITH_DIVERGENCE | **A** |
| code_status | 2 | COMPLETED_WITH_DIVERGENCE | B |
| complete_blood_count | 1 | COMPLETED_WITH_DIVERGENCE | **A** |
| dobutamine | 1 | COMPLETED_WITH_DIVERGENCE | B |
| dopamine | 1 | COMPLETED_WITH_DIVERGENCE | B |
| crrt | 3 | COMPLETED | B |
| enzyme | 1 → 2 | reopened, RUNNING | **A** — attempt_0002 SQL is already fixed |
| epinephrine | 1 | BLOCKED_REPRESENTATION | B — `retry`, not `reopen` |
| gcs | 1 → 2 | VALIDATING_DEMO, shape_ok | B — **fixed**, ready for the full run |
| height | 1 | VALIDATING_FULL | B — in flight, HPC job 29715902 live |

Clean, for contrast: `age`, `bg` (att 6), `blood_differential`, `chemistry`
(att 3), `coagulation` (att 4). All converged to the bare cast after several
attempts — the concepts that finished in 1–2 attempts are the ones that kept
the hedge.

## Notes

- **`crrt` is the only exact match in the set.** Reopening it takes `status`
  from `1/65 exact match` to `0/65` until it re-completes.
- **`complete_blood_count`, `dobutamine`, `dopamine`, `crrt`** already have
  committed metrics (`metrics/<c>/run_0001.json`), so a fresh goal opens run 2
  and the run-scoping keeps the two apart.
- **`acei`, `antibiotic`, `arb`, `cardiac_marker`, `code_status`** have no
  metrics binding or output at all — those ports predate the plugin. Their
  reopened goal will be recorded as run 1.
- All nine reopen targets are level 0 with no interdependencies, so order does
  not matter. Their dependents are all PENDING.
- `epinephrine` and `height` are **not** reopened — `epinephrine` uses `retry`
  from its block, and `height` has a live HPC job (29715902); poll it rather
  than killing it, that run is already spent.

## gcs — done 2026-08-11

Fixed in place rather than reopened, because it had not spent a full run yet.

- One occurrence, mapping `Observation.effective_datetime` → `charttime`.
  Replaced the 10-line `TRY_TO_TIMESTAMP(REGEXP_REPLACE(...), pinned-format)`
  block with `TRY_CAST(o.effective_datetime AS TIMESTAMP_NTZ)`.
- **`charttime` is load-bearing beyond its own column here.** It is stringified
  into the UUIDv5 name that witnesses `No Response-ETT`
  (`CONCAT(stay_id, '-', CAST(charttime AS STRING), '-223900-No Response-ETT')`,
  plus a `- INTERVAL 1 HOUR` variant covering the ETL's DST-gap normalisation).
  A changed parse could have silently broken the ETT discriminator.
- `cast-probe` says it does not, on demo: **3,279 rows both sides, zero
  difference**, no schema change. Not proof — 100 patients, and date-only
  `effective_datetime` values may simply not occur in the demo cohort, which is
  exactly the case the pinned format was NULLing. The full run settles it.
- Route: `fail --counter semantic` (the only legal exit from `VALIDATING_DEMO`)
  → `retry` → attempt_0002 → ViewDefinitions copied from attempt_0001, fixed
  SQL staged → `run-demo` **shape_ok** → `validate-demo`.
- Now `VALIDATING_DEMO` attempt 2, resume plan: *re-enter at 6 (full-data run)*.
  `/goal gcs` picks it up at the HPC leg; the demo gate is already satisfied.
- attempt_0001 is left intact as the record of the withdrawn port, with the
  reason in its `error_message`.

## Cheap falsification before spending a full run

```
uv run mimic_utils cast-probe <concept> --variant-sql /path/to/new.sql
```

Runs both SQL variants on the demo warehouse, diffs the parquets, exits 1 if the
edit is semantic. Touches no state and consumes no attempt. A clean result is
**not** evidence of equivalence — 100 patients, and these divergences run
&lt;0.01% of rows — it only means no cheap objection was found.

  /goal cardiac_marker      /goal complete_blood_count    /goal acei
  /goal antibiotic          /goal arb                     /goal code_status
  /goal crrt                /goal dobutamine              /goal dopamine
