# HPC poller — attempt_0002, job 29721291

## Poll outcome
- Command: `uv run mimic_utils hpc-poll antibiotic` (job id from `hpc_job.json`: 29721291)
- Outcome: **complete** — `comparison.full.json` fetched
- Verdict: **review** (exit code 2)
- Polls before completion: 2; Slurm elapsed runtime: **58 s** (sacct, `hpc_accounting.json`), state COMPLETED
- Job left the queue normally; verdict artifact exists, so this is a real verdict, not a crash.

## Comparator details (from `comparison.full.json`)
- Comparison mode: `full_tuple_multiset` (no unique key)
- Schema identity: **match** — 7 columns, identical names/types, no missing/extra, no incompatible types
  - columns: subject_id, hadm_id, stay_id, antibiotic, route, starttime, stoptime
- Row count: candidate 735,462 vs oracle 735,462 (delta 0, NOT gated, match=True)
- Identical rows: 691,939 / 735,462 (94.08%)
- Differing rows: 43,523 (residual paired 1:1 on antibiotic, hadm_id, route, subject_id, anchored by subject_id+hadm_id)
- `only_oracle`: 0, `only_candidate`: 0 (the 43,523 multiset halves are the two sides of the substituted rows, not invented rows)

## Divergence classification
- Classification: `paired_residual`
- Tier: **contested** (judge_required=True, diagnostician_required=True)
- Blocking class: `differing_conflict` × 70 (0.010% of oracle rows)
  - column starttime: 52 conflicting rows
  - column stoptime: 23 conflicting rows
- Gap-shaped: `differing_null_only` × 43,453
  - stoptime NULL in candidate: 43,422
  - starttime NULL in candidate: 43,369
  - stay_id NULL in candidate: 13,494
- Conflict attribution: attempted=true, cause `upstream_timestamptz_dst_shift` (America/New_York TIMESTAMPTZ round-trip),
  attributed_rows=67, complete=false, residual_rows=3 unexplained
  - citations: `mimic-fhir/sql/fhir_encounter.sql:65`, `mimic-fhir/sql/fhir_medication_request.sql:43-44`
  - Tier stays `contested` on the 3 residual rows.

## Notable issue — run_meta.full.json never produced on the node
`comparison.full.json` was written successfully, but the job then crashed writing `run_meta.full.json`
with `TypeError: Object of type datetime is not JSON serializable` in `full_runner._write_run_meta`
(line 285, json.dumps of the meta dict). The `divergence` dict embedded in run_meta still carries raw
`datetime` objects (the comparison JSON path serialises them; the run_meta path does not). Consequently
`run_meta.full.json` does not exist on the node and nothing was fetched locally. This does NOT invalidate
the verdict — the verdict artifact exists and is authoritative. Flagging for diagnosis; no implementation
artifact was modified.

## Fetched artifacts
- `comparison.full.json` — fetched (verdict: review)
- `run_meta.full.json` — NOT produced/fetched (job crashed writing it; see above)
- `hpc_accounting.json` — written from sacct (elapsed 58 s, state COMPLETED)
- `slurm-29721291.out` — queried remotely for the crash trace

## Evidence
No implementation artifacts modified; nothing committed. Verdict `review` should route to the equivalence judge (tier contested).