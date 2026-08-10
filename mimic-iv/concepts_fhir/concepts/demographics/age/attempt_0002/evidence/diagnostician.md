# Mismatch Diagnosis Evidence: `age` (attempt_0002, full run 1)

**Stage:** mismatch-diagnostician
**Date:** 2026-08-07
**Concept:** demographics/age
**Source verdict:** `mismatch` (blocking `differing_conflict` = 504 rows)

## Verdict class breakdown (from comparison.full.json)

- Row count: candidate 431,231 = oracle 431,231 (NOT gated)
- Schema: match (6 columns, no missing/extra, no type issues)
- `differing_conflict` (BLOCKING): 504 rows
  - `age` conflicts on **460** rows — candidate ~2 years HIGHER than oracle
    (one sample +6). Examples: subject 12047822 (oracle pair
    (anchor_age=91, anchor_year=2165) → birth 2074; candidate → 2072), +2.
  - `admittime` conflicts on **44** rows — candidate exactly +1 hour
    (03:10 vs 02:10).
- `differing_null_only` (review-shaped, declared unrepresentable): 430,727 rows
  on anchor_age/anchor_year (each NULL in candidate on 431,231 rows).
- `only_candidate`: 0, `only_oracle`: 0.

## Root cause — confirmed against upstream ETL source

1. **`age` +2y (460 rows)** — `mimic-fhir/sql/fhir_patient.sql:15`:
   `birthDate = CAST(CAST(MIN(tfs.intime) AS DATE) - CAST(anchor_age||'years'
   AS INTERVAL) AS DATE)`. So FHIR `birthDate` is **`MIN(transfers.intime) -
   anchor_age`**, NOT `anchor_year - anchor_age`. The port's
   `year(admittime) - year(birthDate)` equals the canonical
   `anchor_age + DATETIME_DIFF(...)` only where
   `year(MIN(transfers.intime)) == anchor_year` — holds ~99.9% (the demo's
   100 patients all satisfy it), fails on ~460 full-data patients whose
   earliest transfer year is before the anchor year. No exact recovery; the
   candidate is as faithful as the data allows. → **representability gap**
   (data/IG), NOT a port bug.
2. **`admittime` +1h (44 rows)** — `mimic-fhir/sql/fhir_encounter.sql:65`:
   `CAST(adm.admittime AS TIMESTAMPTZ)`. A wall-clock time in the DST
   spring-forward gap (e.g. nonexistent 02:10 on a March Sunday) is normalised
   to 03:10 before being written to `period.start`; the original is
   unrecoverable. The port's `CAST(period.start AS TIMESTAMP_NTZ)` faithfully
   preserves the already-shifted value. → **representability gap** (data-IG
   transformation loss), NOT a port bug.

## Classification

- `age`: representability gap (upstream birthDate synthesis). Unfixable in SQL.
- `admittime`: representability gap (upstream timestamptz DST shift). Unfixable.
- Only the implementer's SQL/ViewDefinition are involved — no portable fix.
  The diagnosis does NOT indict source-analyst or terminology-resolver.
- **fhir-prober carryover over-generalised** the demo's 100/100
  `birthDate.year == anchor_year - anchor_age` result to the full cohort
  without flagging it as demo-only. Invalidate it so a retry re-probes.

## MIMIC_NOTES.md updates requested

Both findings are dataset-wide (affect every age-derived concept / every exact
admittime comparison) and were promoted by the orchestrator:
- "Patient.birthDate is NOT anchor_year - anchor_age — it is
  MIN(transfers.intime) - anchor_age" (updated entry).
- DST-gap +1h admittime shift (added to the FHIR-datetime entry).
