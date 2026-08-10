# carryover — per-concept analysis reused across attempts

Facts about **one concept** that do not change between attempts: which source
columns matter, which codes the SQL names, which FHIR element carries them,
which coding system an itemid uses. A retry reads them instead of re-spawning
the agent that produced them.

Not attempt state, and **not** part of the write-once regime. Attempt artifacts
are immutable; these files are overwritten in place, because the file should
always hold the current best analysis. They record what stays true after an
attempt is superseded.

Distinguish this from the dataset notes: `MIMIC_NOTES.md` and
`MIMIC_NOTES.d/<concept>.md` hold what is true of the **dataset** regardless of
concept; carryover holds what is true of **one concept** regardless of attempt.

## It is read automatically

Phase 3 of the loop begins with `mimic_utils carryover <concept>` and **skips
every stage marked `reuse`**, reading `<concept>/<stage>.md` and passing its
contents to the implementer as if the agent had just produced it
(`.opencode/skills/concept-orchestrator-loop/SKILL.md` → Phase 3). The same
freshness is reported by `mimic_utils resume <concept>` in its `fresh_stages` /
`stale_stages` fields. Two stages carry over — `source-analyst` and
`fhir-prober`. The implementer deliberately has none: its output *is* the
attempt, and carrying it across attempts would defeat the write-once contract.

```
carryover/<concept>/source-analyst.md
carryover/<concept>/fhir-prober.md
carryover/<concept>/carryover.json      # freshness ledger
```

## The CLI

```bash
mimic_utils carryover <concept>                    # which stages are reusable
mimic_utils carryover-record <concept> --stage S   # after writing <stage>.md
mimic_utils carryover-invalidate <concept> --stage S --reason "..."
```

The stage agent writes its own `<stage>.md` and then records it. `carryover.json`
holds, per stage, the attempt that wrote it and whether it has been invalidated;
an unrecorded file is not reused. Never hand-edit the ledger — `record` and
`invalidate` maintain it atomically.

"Not applicable" is a finding worth recording. A stage that determines a concept
needs nothing from it still writes a one-line `<stage>.md` and records it; an
absent file re-spawns that agent on every future attempt.

## Reuse is revocable, and that is what keeps it honest

Reuse is only safe while the analysis is right. A diagnosis that traces a
failure to a stage invalidates it — "mapped the wrong resource" or "wrong coding
system" indicts `fhir-prober` — and the next attempt re-runs it. This is the
load-bearing rule: reusing a wrong analysis is how a loop spends all ten
attempts converging on nothing. A diagnosis that blames only the SQL or the
ViewDefinition invalidates nothing; that is implementer output, which is
attempt-scoped.

Invalidation leaves the markdown in place — the next run overwrites it, and
until then the reason is readable in the ledger. A stage recorded again after
being invalidated becomes fresh again.

## Check a reused file is still true

The ledger tracks invalidation by diagnosis, not by the world moving underneath.
Invalidate by hand if any of these changed since the file was written:

- the warehouse (`MIMIC_FHIR_WAREHOUSE`) or the MIMIC-on-FHIR IG version — both
  invalidate a `fhir-prober` mapping;
- the source concept SQL in `mimic-iv/concepts/` — invalidates a
  `source-analyst` analysis;
- an entry in `MIMIC_NOTES.md` the file cites, if it has since been sharpened or
  contradicted. Check the current text of that entry, not the version the file
  quotes.

Delete a concept's directory once its port reaches a terminal state; the
durable, cross-concept findings belong in the dataset notes, not here.
