# HPC poller evidence

Poll complete. Reporting outcome and verdict as produced by the tool without interpretation, and without spawning any judge or diagnostician.

**Poll outcome:** `complete` (fetched `comparison.full.json` and `run_meta.full.json`; Slurm state COMPLETED)

**Comparator verdict:** `review`

- `divergence.tier`: `contested`
- `divergence.diagnostician_required`: `true`
- `divergence.judge_required`: `true`
- `divergence.classification`: `unavailable_no_key`

**Slurm elapsed runtime:** 180 s (source `slurm_sacct`, state COMPLETED; `run_meta` execute 175.627 s + compare 1.444 s)

**Row counts (not gated):** oracle 665,529 vs candidate 665,550 (delta +21). Residual did not pair (594,266 oracle / 594,287 candidate); no unique key so classes stay `unavailable_no_key`. Schema: `match: true`, with extra columns `icu_encounter_key`, `patient_key` (expected by manifest key but declared-column-in-key void-diff note absent; this was noted by the poller). No incompatible/missing columns.

**Diagnostics lines:**

- `row count (not gated): oracle 665,529 vs candidate 665,550 (delta +21)`
- `RESIDUAL DID NOT PAIR — 594,266 oracle and 594,287 candidate residual rows do not correspond. Their counts being equal proves nothing: it follows from the row counts being equal.`
- `CONTESTED — a value conflict. Either a port bug or upstream ETL transformation loss; the data cannot tell you which: 594,287 × only_candidate (89.295% of oracle rows) — rows in the candidate that are not in the oracle -- but this concept has no unique key, so a row whose only fault is a NULL appears here too ... plus the accept bar (upstream mimic-fhir ETL statement, file and line) and the state-the-fraction instruction.`
- `GAP-SHAPED — consistent with a MIMIC-on-FHIR coverage gap: 594,266 × only_oracle — oracle rows the candidate never produced`
- notes: no unique key, residual did not pair; residual pairing left nothing to align rows on.

**Artifact paths fetched/read:**

- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/hpc_accounting.json`
- Candidate full parquet remains on scratch at `/scratch3/nau025/mimic-code/.../attempt_0001/candidate.full.parquet/`.

No diagnosis, judge/diagnostician, or commit was performed.
