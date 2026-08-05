---
name: hpc-transfer
description: Stage a concept port to the CSIRO HPC (Petrichor) for full-MIMIC execution and fetch results back. Defer to paper_reproductions/.claude/skills/hpc-transfer/ and csiro-hpc/ skills for all transfer conventions, cluster paths, and Slurm templates. Requires environment preflight before first use. Trigger phrases include "transfer to HPC", "run on cluster", "submit to Petrichor", "fetch HPC results".
---

# hpc-transfer

Staging a concept port to the Petrichor HPC cluster for full-MIMIC
execution and fetching results back.

## Authoritative references

**All cluster conventions, SSH targets, paths, account details, Slurm
templates, and transfer procedures are defined in the paper_reproductions
skills** — these are the sole source of truth:

- `../master_thesis_pipeline/paper_reproductions/.claude/skills/hpc-transfer/SKILL.md`
- `../master_thesis_pipeline/paper_reproductions/.claude/skills/csiro-hpc/SKILL.md`

This skill only adds concept-port-specific framing; never invent or override
cluster details. Read both referenced skills before any HPC operation.

## Environment preflight

Before first use, verify HPC connectivity and environment:

1. SSH key-based access to `petrichor.hpc.csiro.au` works.
2. Required remote directories exist on `$SCRATCH3DIR`.
3. The remote Python environment (3.12-compatible) is available.
4. The remote Spark/FHIR warehouse is accessible.

Run a smoke test (as described in the `hpc-transfer` skill) before
submitting any batch job.

## Concept port specifics

### What to transfer

For concept `<name>` attempt `<NNNN>`:

```
mimic-iv/concepts_fhir/concepts/<category>/<name>/attempt_NNNN/
  ├── ViewDefinition.<label>.json  # one per projected FHIR resource
  ├── concept.sql                  # the sql-view Library SQL
  └── evidence/              # one write-once evidence file per stage
```

Plus the original concept SQL for the comparator:
`mimic-iv/concepts/<category>/<name>.sql`

### Execution

1. **Provision** — register the ViewDefinition and Library on the
   remote Pathling server (same flow as local, but targeting the
   production Pathling endpoint).
2. **Read the oracle** — the full derived concept is **already computed** in
   the read-only DuckDB oracle at
   `/scratch3/nau025/oracle/mimic4-full.db`. Never recompute it: it is an
   immutable artifact built once by `mimic_utils.build_full_oracle`.
3. **Run ported** — execute the ported `concept.sql` via Pathling
   `$sqlquery-run` against full MIMIC-on-FHIR.
4. **Compare** — run the deterministic comparator.
5. **Fetch** — rsync results back to the concept port's attempt
   directory under `expected/`.

### Slurm conventions

Defer entirely to the `hpc-transfer` and `csiro-hpc` skills for:
- Account (`--account=<code>`)
- Partition and wall time
- Module loads
- SSH target and paths
- `submit.slurm` template
- Smoke test procedure on login node
- Poll interval (300s for auto-repro loops)
- Result fetch rsync

## Polling and fetch

See the `hpc-transfer` skill's "Automated path" section and the
`hpc-poller` subagent for the exact polling loop, fatal-marker
detection, and result-fetch procedure.

## State markers

- `expected/run_meta.json` — metadata with `generated_at` timestamp
- `expected/comparison.json` — the comparator output
- `slurm-<job_id>.out` — retained on crash only
