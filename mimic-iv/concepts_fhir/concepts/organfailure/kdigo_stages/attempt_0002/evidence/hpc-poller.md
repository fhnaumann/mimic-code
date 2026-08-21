# HPC poller evidence — kdigo_stages attempt_0002

## Command
`uv run mimic_utils hpc-poll kdigo_stages`

## Queue outcome
- **outcome: `complete`** — job 30319339 left the queue (Slurm state `COMPLETED`), a fresh `comparison.full.json` was fetched. Not a crash; no fatal markers (Traceback/OutOfMemory/slurmstepd/CANCELLED/Error) were hit during polling.
- polls before completion: 3 (300 s interval)
- Slurm elapsed runtime (sacct, `hpc_accounting.json`): **491 s**, source `slurm_sacct`, state COMPLETED, started 2026-08-21T14:10:54, ended 2026-08-21T14:19:05
- run_meta timings: execute 485.039 s, compare 2.762 s

## Comparator verdict
- **verdict: `review`** (exit code 2). The run succeeded; this is NOT a failed port — the equivalence judge is to be spawned.
- `divergence.tier`: **`contested`**
- `divergence.diagnostician_required`: **true**
- `divergence.judge_required`: **true**
- `divergence.classification`: `unavailable_no_key`
- `match`: false; schema: **match** (18 actual columns = 15 expected + 3 extra FHIR keys patient_key/encounter_key/icu_encounter_key; no incompatible types, no missing columns).

## Row counts (reported, not gated)
- oracle: **4,011,255**
- candidate: **4,011,012**
- delta: **−243** (0.006% of oracle)
- residual: 1,703 oracle vs 1,460 candidate rows did not pair (full-tuple multiset comparison; no unique key, residual pairing anchored=false, paired=0, all 15 value columns substituted).

## Divergence classes
- `only_oracle` (gap-shaped): **1,703** — oracle rows the candidate never produced; the shape a legitimate MIMIC-on-FHIR coverage gap takes.
- `only_candidate` (contested/blocking): **1,460** (0.036% of oracle rows) — rows in the candidate not in the oracle; with no unique key, a row whose only fault is a NULL appears here too, so invented rows and NULL divergence are indistinguishable. Treat as a bug unless evidence positively shows otherwise.
- `attributed`: empty. `unresolvable`: empty. `declared_unrepresentable`: empty.
- note: divergence classes cannot be separated (no unique key, residual did not pair); the judge reasons with strictly less evidence than a keyed concept would provide.

## Judge bar (verbatim from comparison)
A conflict is not gap-shaped, so an absent element does not explain it. An accept must cite the upstream mimic-fhir ETL statement (file and line) that writes a different value than relational MIMIC-IV holds, and show the oracle value is not recoverable from what FHIR does carry by ANY query — not merely that this port did not recover it. Absent that citation the answer is `bug`. State the affected fraction.

## Diagnostics lines (verbatim)
1. row count (not gated): oracle 4,011,255 vs candidate 4,011,012 (delta -243)
2. RESIDUAL DID NOT PAIR — 1,703 oracle and 1,460 candidate residual rows do not correspond. Their counts being equal proves nothing: it follows from the row counts being equal.
3. CONTESTED — a value conflict. Either a port bug or upstream ETL transformation loss; the data cannot tell you which:
4. 1,460 × only_candidate (0.036% of oracle rows) — rows in the candidate that are not in the oracle -- but this concept has no unique key, so a row whose only fault is a NULL appears here too. Invented rows and NULL divergence are INDISTINGUISHABLE for this concept; treat as a bug unless the evidence positively shows otherwise
5. bar for an accept: … (see Judge bar above)
6. GAP-SHAPED — consistent with a MIMIC-on-FHIR coverage gap:
7. 1,703 × only_oracle — oracle rows the candidate never produced; this is the shape a legitimate MIMIC-on-FHIR coverage gap takes
8. note: No unique key for this concept, and the residual did not pair: divergence classes cannot be separated. The judge is reasoning with strictly less evidence than a keyed concept would provide.
9. note: residual pairing: every column differs between the residuals; there is nothing left to align rows on, so the residual cannot be shown to be substitutions rather than invented and missing rows

## Artifacts fetched / written
- fetched: `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0002/comparison.full.json`
- fetched: `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0002/run_meta.full.json`
- accounting written: `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0002/hpc_accounting.json`
- this evidence: `mimic-iv/concepts_fhir/concepts/organfailure/kdigo_stages/attempt_0002/evidence/hpc-poller.md`

## Routing note
Spawn the equivalence judge (`equivalence-judge`), carrying `divergence.tier=contested`, `divergence.judge_required=true`, `divergence.diagnostician_required=true`, and classification `unavailable_no_key`. Do not relaunch a job; do not treat `review` as a failure.