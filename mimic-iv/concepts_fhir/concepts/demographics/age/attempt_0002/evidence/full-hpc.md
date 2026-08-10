# Full-Data HPC Evidence: `age` (attempt_0002, run 1)

**Stage:** hpc-launcher + hpc-poller
**Date:** 2026-08-07
**Concept:** demographics/age
**Attempt:** attempt_0002

## Launch

- Command: `uv run mimic_utils hpc-launch age`
- Smoke test (login node): PASSED (warehouse OK, oracle OK, imports OK)
- Job id: 29567537
- Remote path: /scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0002
- hpc_job.json: mimic-iv/concepts_fhir/concepts/demographics/age/attempt_0002/hpc_job.json
- submit.slurm: attempt_0002/submit.slurm (64 cores, 503g, exclusive, 2:00:00)

## Poll

- Command: `uv run mimic_utils hpc-poll age`
- Outcome: complete (no fatal markers, comparison fetched)

## Verdict: MISMATCH (blocking)

- Row count: candidate 431,231 = oracle 431,231, delta 0 (NOT gated)
- Schema: match (6 columns identical, no missing/extra, no type issues)
- `differing_conflict` (BLOCKING): 504 rows
  - `age` conflicts on 460 rows (candidate ~2 years HIGHER than oracle)
  - `admittime` conflicts on 44 rows (exactly 1 hour higher: 03:10 vs 02:10)
- `differing_null_only` (review-shaped, declared unrepresentable): 430,727 rows
  - anchor_age NULL in candidate on 431,231 rows
  - anchor_year NULL in candidate on 431,231 rows
- `only_candidate`: 0
- `only_oracle`: 0
- identical_rows: 0

## Artifacts fetched

- attempt_0002/comparison.full.json
- attempt_0002/run_meta.full.json (engine pathling-embedded, execute 19.5s, compare 1.3s)

## Interpretation

The declared-unrepresentable anchor columns behave exactly as designed (typed
NULL → differing_null_only, review-shaped). But the blocking `differing_conflict`
class (age +460 / admittime+44) is present and CANNOT be explained by a coverage
gap. This is a real value conflict → routes to Phase 5 (mismatch-diagnostician).
The judge is NOT called.
