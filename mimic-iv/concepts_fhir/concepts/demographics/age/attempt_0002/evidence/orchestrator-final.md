# Orchestrator Final Evidence: `age`

**Concept:** demographics/age
**Attempt:** attempt_0002 (retry of attempt_0001)
**Terminal state:** BLOCKED_REPRESENTATION
**Full HPC runs consumed:** 1
**Verdict:** mismatch (blocking differing_conflict, intrinsic representability gap)
**Result:** [goal:blocked]

## Loop trace

1. **Phase 1 (resume):** `mimic_utils resume age` returned `start_new_attempt`
   (attempt_0001 had failed the demo shape gate on `subject_id`/`hadm_id`
   VARCHAR vs INTEGER). Applied `resume --apply` → `fail`→`start` → created
   attempt_0002. Reuse: source-analyst, fhir-prober. Re-run: terminology-resolver.
2. **Phase 3:** terminology-resolver confirmed "not applicable" (no coded
   fields), recorded reusable carryover (`carryover/age/terminology-resolver.md`).
3. **Phase 5 (held diagnosis, skipped diagnostician):** implementer fixed the
   only attempt_0001 bug — cast `subject_id`/`hadm_id` to INTEGER, kept
   TIMESTAMP_NTZ, typed NULLs for anchor_age/anchor_year (declared
   unrepresentable), age = year(admittime)-year(birthDate) as BIGINT.
4. **Phase 4 (demo):** `run-demo` → **SHAPE OK** — 6 columns, correct types,
   275 rows. Cheap shape gate only.
5. **Phase 6 (full, run 1):** `hpc-launch` (job 29567537, smoke PASS) →
   `hpc-poll` → verdict **mismatch**.
6. **Phase 5 (diagnose full mismatch):** mismatch-diagnostician traced both
   conflicts to **upstream ETL source**, classified both as intrinsic
   representability gaps, not port bugs. Invalidate fhir-prober carryover
   (over-generalised demo 100/100 anchor relation).
7. **Phase 7/8:** judge NOT convened — the verdict is `mismatch` (blocking
   `differing_conflict`), which the judge cannot override and which is never
   routed to the judge. Recorded `block` → BLOCKED_REPRESENTATION.

## Full-data divergence classes (attempt_0002 comparison.full.json)

| Class | Count | Interpretation |
|---|---|---|
| row_count | 431,231 = 431,231 | match, NOT gated |
| schema | match | 6 columns, no missing/extra/type issues |
| `differing_conflict` (BLOCKING) | 504 | age 460, admittime 44 |
| `differing_null_only` (review-shaped) | 430,727 | anchor_age/anchor_year (declared unrepresentable) |
| `only_candidate` / `only_oracle` | 0 / 0 | none |

## Root cause (upstream-ETL-confirmed representability gaps)

- **`age` +2y (460 rows):** `mimic-fhir/sql/fhir_patient.sql:15` synthesises
  `Patient.birthDate = MIN(transfers.intime) - anchor_age`, NOT
  `anchor_year - anchor_age`. The port's `year(admittime) - year(birthDate)`
  equals the canonical `anchor_age + DATETIME_DIFF(...)` only where
  `year(MIN(transfers.intime)) == anchor_year` (~99.9% of rows). Those ~460 are
  patients whose earliest transfer year precedes the anchor year. No exact
  recovery exists from FHIR.
- **`admittime` +1h (44 rows):** `mimic-fhir/sql/fhir_encounter.sql:65` casts
  admittime through `TIMESTAMPTZ`; DST spring-forward gap times (e.g. the
  nonexistent 02:10) are normalised to 03:10 and the raw value is
  unrecoverable. The port's TIMESTAMP_NTZ cast faithfully preserves the
  already-shifted value.

The port is **as faithful as the data allows** — but the canonical oracle
values for `age` (on those 460) and `admittime` (on those 44) cannot be
reproduced by any SQL/ViewDefinition, because the FHIR data itself encodes
different values. No retry can reach `match` (the `admittime` conflict is
irreducibly blocking on its own).

## MIMIC_NOTES.md entries updated (dataset-wide quirks)

1. **`Patient.birthDate` is NOT `anchor_year - anchor_age` — it is
   `MIN(transfers.intime) - anchor_age`** — rewrote the previous ("encodes the
   anchor pair") entry. The demo-validated 100/100 anchor relation does NOT
   hold on full data; year-subtraction age diverges ~0.1%. Affects every
   age-derived concept (creatinine_baseline, oasis, charlson, sapsii).
   Verified: full-data age attempt_0002, 460 differing_conflict + upstream
   fhir_patient.sql:15.
2. **DST-gap admission times are irreversibly shifted +1h** — added to the
   "FHIR datetimes carry an offset" entry. Verified: age attempt_0002, 44
   admittime conflicts, upstream fhir_encounter.sql:65.

## Carryover mutation

- `carryover/age/fhir-prober.md` invalidated (reason: demo-only anchor
  relation over-generalised to full data).
- `carryover/age/terminology-resolver.md` recorded (not applicable).

## Artifacts

- attempt_0002: ViewDefinition.patient.json, ViewDefinition.encounter.json,
  concept.sql, unrepresentable.json, candidate.demo.parquet, shape.demo.json,
  submit.slurm, hpc_job.json (job 29567537), comparison.full.json,
  run_meta.full.json, evidence/{terminology-resolver,implementer,demo-runner,
  full-hpc,diagnostician,orchestrator-final}.md
- state: BLOCKED_REPRESENTATION (semantic_counter=1, engineering=3, hpc=1)

## Conclusion

`age` is blocked for human review as an **intrinsic representability**
exception. The port is faithful; the divergence is a property of the
MIMIC-on-FHIR data itself (birthDate base + DST-shifted admittime), confirmed
in the upstream ETL source. Not `[goal:complete]`, not
`[goal:complete-with-divergence]` — the comparator's `mismatch`/blocking
`differing_conflict` is a hard gate the judge cannot override, so the verdict
is a representability blocker.
