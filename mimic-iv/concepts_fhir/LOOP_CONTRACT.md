# Loop contract — MIMIC-IV → MIMIC-on-FHIR concept port

Authoritative statement of what the loop compares, where, and what gates what.
Where this file and any agent prompt, skill, or README disagree, **this file wins**
and the other document is a bug.

Decided 2026-08-05. Row-count gating revised 2026-08-06. Conflict gating
revised 2026-08-07 — see "MIMIC-on-FHIR is a transform, not a subset".
Concurrency revised 2026-08-10 — see "Concurrency: waves of parallel goals".

## What is being claimed

For one named derived concept, two *different* queries must produce the *same table*:

- **Oracle** — the canonical MIMIC-IV SQL (`mimic-iv/concepts/`), run over relational
  MIMIC-IV 2.2.
- **Candidate** — a FHIR ViewDefinition + SQL authored by the agent, run over
  MIMIC-on-FHIR 2.1 through Pathling.

The port is not "the same query on two datasets". There is no `admissions` table in
FHIR. It is two unrelated queries whose output tables must agree, which is why the
comparison *is* the experimental claim rather than a smoke test attached to one.

## The oracle is computed once

| | |
|---|---|
| Path | `/scratch3/nau025/oracle/mimic4-full.db` (HPC, Lustre) |
| Contents | 22 `mimiciv_hosp`, 9 `mimiciv_icu`, 65 `mimiciv_derived` tables |
| Derived rows | 72,221,096 |
| Engine | DuckDB 1.5.5 |
| Built by | `mimic_utils.build_full_oracle` |
| Contract | `mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json` |

Immutable. The loop never recomputes it. Rebuild only if the concept SQL baseline
moves off commit `3a914fc`, and then regenerate the manifest in the same pass.

The manifest is the artifact that travels to the laptop: per concept, the exact row
count, columns and types, the natural key, and an order-independent content hash.
An agent reads the manifest to learn the target shape without touching the 14.5 GB
oracle.

## Comparison method

Keyed row-level diff, executed as DuckDB SQL. Never materialise rows into Python —
`vitalsign` alone is 9.7M rows.

- **52 concepts** have an empirically-unique key → full outer join on that key,
  then per-column value comparison. Reports rows only-in-oracle, only-in-candidate,
  matched-but-differing (**and which column** differs), and identical.
- **13 concepts** have no unique key within 3 columns → full-tuple multiset
  comparison. Complete, but names no column, so it is less diagnostic.

## Row count is evidence, not a verdict

MIMIC-on-FHIR does not carry everything relational MIMIC-IV carries. A candidate
can be a faithful port and still return fewer rows, so **an exact row count is
not a hard gate** and the comparator does not decide those cases — the judge does.

But "counts differ by 12,043" cannot distinguish a legitimate coverage gap from a
wrong window, so the comparator never hands the judge that number alone. The keyed
diff decomposes the delta into classes with different meanings:

| Class | Meaning | Can a coverage gap cause it? |
|---|---|---|
| `only_oracle` | oracle rows the candidate never produced | **Yes** — this is what a gap looks like |
| `differing_null_only` | key-matched, candidate NULL where oracle has a value | **Yes** — the FHIR element does not exist |
| `only_candidate` | rows the candidate invented | **No** |
| `differing_conflict` | key-matched, both sides hold values, they disagree | **No** |

## MIMIC-on-FHIR is a transform, not a subset

The two "No" rows above are true and were, until 2026-08-07, read as one thing
too many. "A coverage gap cannot cause it" was treated as "the port is wrong",
and conflicts hard-failed without reaching the judge.

That inference is false, because a coverage gap is not the only thing
MIMIC-on-FHIR does to MIMIC-IV. It also **rewrites values**:

- `mimic-fhir/sql/fhir_patient.sql:15` synthesises `Patient.birthDate` as
  `MIN(transfers.intime) - anchor_age`, **not** `anchor_year - anchor_age`.
  The two agree on ~99.9% of patients and disagree on the rest.
- `mimic-fhir/sql/fhir_encounter.sql:65` casts `admittime` through `TIMESTAMPTZ`,
  so a wall time inside the DST spring-forward gap is normalised forward an hour
  and the original is gone.

Neither is a missing element. Both produce key-matched rows whose values
disagree, and **no candidate query can invert either** — the information is not
in the FHIR data to recover. A port that hits these is as faithful as the data
allows and was being failed for it.

So a conflict has two possible causes — a port bug, or upstream transformation
loss — and they are **identical in the data**. The comparator cannot tell them
apart, and neither can any amount of retrying. What it can do is name the shape
it saw and route the case to the judge at the right evidentiary bar.

**Expect this to be common.** Not one table maps cleanly. A verdict vocabulary
in which the normal case is a hard failure is measuring the wrong thing.

### Verdicts

| Verdict | Reached when | Judge? |
|---|---|---|
| `match` | nothing diverged | never called |
| `mismatch` | a **machine-provable contradiction**: the candidate did not execute, the schema is wrong, or a declaration the candidate's own data refutes | never called — there is nothing to weigh |
| `review` | anything else that diverged | **decides**, at the tier's bar |

`mismatch` is now narrow on purpose. It means "this result is not comparable, or
the port contradicted itself" — never "these values look wrong to me".

### The three review tiers

`divergence.tier` and `divergence.judge_bar` are in every comparison artifact.

| Tier | Present | What an `accept` must establish |
|---|---|---|
| `gap_shaped` | only `only_oracle` / `differing_null_only` | the **FHIR element or path that does not exist**, that it explains the magnitude and shape, and that every defensible mapping was tried |
| `contested` | `differing_conflict` or `only_candidate` | all of the above **plus** the **upstream `mimic-fhir` ETL statement (file and line)** that writes a different value than relational MIMIC-IV holds, and that the oracle value is unrecoverable by **any** query — not merely that this port did not recover it |
| `attributed` | `differing_conflict` **only**, and the comparator replayed it to a known upstream ETL cast on **every** conflicting row | the citation is already in the artifact, so instead: that one cited statement writes the FHIR element **this** column is sourced from, and that the attributed fraction is consistent with the transformation's rarity |

A conflict outranks a gap: a result with both is `contested`. The raised bar is
what keeps the relaxation honest — a conflict is not presumed to be a bug, and
is **not presumed to be intrinsic either**. Without the ETL citation the answer
is `bug`, and the loop continues exactly as before.

**`attributed` is the one case where the comparator supplies the citation
itself.** `mimic-fhir` casts naive MIMIC wall times through `TIMESTAMPTZ`, which
rewrites a DST spring-forward wall time irreversibly — and that cast is
*replayable*, so the comparator round-trips the oracle value through
`America/New_York` and checks it reproduces the candidate, per row, over the
whole conflict set. It is a stronger proof than an agent inferring the same
thing from a bounded sample, and it is why the diagnosis is skippable here:
`divergence.diagnostician_required` is `false` and the loop routes straight to
the judge.

Its limits are part of the contract, not implementation detail:

- **It never yields `match`, and it never skips the judge.** The values do
  differ from the oracle; accepting that is a ruling.
- **All-or-nothing.** A partly explained conflict set stays `contested` and
  `diagnostician_required` stays `true` — the unexplained rows set the bar. The
  artifact still records which rows are accounted for, so the diagnosis is
  scoped to the residual.
- **It proves the operation, not the provenance.** `attributed[].citations` is
  the set of known ETL sites, not a per-column proof.
- **A large attributed fraction argues against the attribution.** DST-gap wall
  times are one hour a year; the judge answers `bug` when the fraction does not
  fit that. This is the check that stops the tier becoming a rubber stamp.
- **If the zone rules available at comparison time do not reproduce the ETL's,
  nothing is attributed.** A canary establishes that before any row is judged.

### The shift can land in the key, and that used to be invisible

Revised 2026-08-12. Attribution above partitions the **conflict** set, and a
conflict is something the comparator can only see in a column it *compares* —
a value column. When the shifted datetime is part of the natural key, the row
never reaches the comparison at all: the oracle row fails to find its partner
and lands in `only_oracle`, the candidate row lands in `only_candidate`, and
one upstream transformation is billed as a missing row **plus** an invented
one — splitting it across both tiers and putting `only_candidate`, a contested
class, on a port that invented nothing.

This was not hypothetical. Six chartevents concepts key on `charttime`. Every
one of them recorded `conflict_attribution: {"attempted": false}` and had the
`attributed` route structurally closed to it. Five then reached `COMPLETED`
by **reconstructing the ETL's `Observation.id` UUIDv5** to detect and undo the
shift inside the port, and `code_status` did it with nine hardcoded UUID
literals read off its own first divergence report. The loop rewarded inverting
an ETL implementation detail because it had closed off the honest answer.

So the comparator now replays the same cast against the **key**: it re-keys the
unpaired oracle rows and checks whether they pair with the unpaired candidate
rows, by semi-join over both sets in full. The result is `key_attribution`,
carried in every comparison artifact beside `conflict_attribution`.

Its limits are the conflict case's, plus one:

- **All-or-nothing on _both_ sides.** A residual `only_candidate` row the
  replay does not reach is still a row the port invented, however tidy the
  oracle side looks. Either side short leaves the tier where it was.
- **The replay must be non-identity.** A row whose key survives the round trip
  unchanged would have paired in the first place; requiring the shift
  explicitly stops attribution becoming a licence to relabel any one-hour error
  as intrinsic.

**The judge's bar carries an extra clause here, and it is the point of the
change:** a port that recovers the pre-shift value by reconstructing a resource
id is refused. The shift is intrinsic; inverting the ETL's id-generation is not
a mapping, no consumer of the IG could reproduce it, and it turns "the served
data does not carry this" into "the served data carries this, encoded in the
primary key". `src/mimic_utils/sql_lint.py` refuses the construction
mechanically (`hardcoded-resource-id`, `resource-id-inversion`) so the argument
does not have to be won again per attempt.

This is an **opaque-identity boundary**, not a ban on joins. A FHIR resource or
reference id may be compared for equality to join resources, group or
deduplicate one resource, and retain provenance. It may not be parsed,
regenerated from guessed source inputs, brute-forced over candidate values,
matched against hardcoded row ids, or otherwise used to infer a source value.
Identity can establish which resource is which; it cannot become a semantic
side channel. The prohibition applies even when the ETL source makes the id
algorithm known and the recovery is exact on every measured row.

**No floor.** A divergence of any size reaches the judge; there is no coverage
threshold below which the loop auto-fails, and none above which it auto-accepts.
The judge argues every case from the IG and the ETL source rather than from an
arbitrary percentage. Magnitude is still evidence — the artifact reports the
affected fraction per column — but it is never the argument.

**The judge is never skipped; the diagnostician is.** Those are separate
decisions and the artifact states each: `divergence.judge_required` is `true` for
every `review` tier without exception, and
`divergence.diagnostician_required` is the only stage a machine proof is allowed
to remove.

### Fidelity is reported twice when a declaration is confirmed

A declared-and-confirmed unrepresentable column is 100% NULL by design, which
makes **every** row differ. `age` therefore reports `0 of 431,231 rows
reproduced identically (0.00%)` while reproducing every representable value on
430,727 of them. The headline is an artifact of the declaration, not a statement
about the port.

So the artifact carries both `identical_fraction` and, whenever a declaration was
confirmed, `representable_fraction` — the same count over the columns the port
could ever have produced, with `representable_excludes` naming what was left out.
Report both. The first is the honest total; the second is the one about the port.

### Unrepresentable columns: emit NULL, never an estimate

Some oracle columns have no MIMIC-on-FHIR representation at all — not "the
element is null on these rows" but "no element carries this, ever". The worked
example is `age`: MIMIC-on-FHIR stores only `Patient.birthDate`, whose year is
`anchor_year - anchor_age`, so the pair is collapsed into its difference and
neither can be recovered. 62 of 100 demo patients share a birth year with
another patient holding a *different* anchor pair.

For such a column the port **must emit a typed NULL** (`CAST(NULL AS SMALLINT)`,
not a bare `NULL`, which Spark types as `void` and fails the type check).

This is the rule most likely to be got wrong, because the two options are
inverted from how they look:

| What the port emits | Divergence class | Consequence |
|---|---|---|
| typed NULL | `differing_null_only` | `gap_shaped` — the lower bar |
| a best estimate | `differing_conflict` | `contested` — the raised bar, needing an ETL citation the estimate does not have |

`anchor_year` is recoverable at ~99% via `min(year(Encounter.period.start))`.
Using it would look like the more diligent choice and would push the whole
result to `contested` over the ~1% that disagree — where the port would have to
argue that its own approximation is intrinsic, which it cannot, because the
NULL was available. Do not substitute a near-miss for an absence. An
approximation is only admissible if it is exact; otherwise it is a conflict.

The relaxation of conflict gating does **not** soften this rule. It widens what
the judge may forgive in the *data*; it does not forgive a port that manufactured
the conflict itself.

Never drop the column. Shape is total — the demo gate fails on any missing
column, dependent concepts would break with a `column not found` crash instead
of a classified verdict, and a dropped column produces no evidence, whereas a
NULL column produces per-column counts the judge rules on and the thesis cites.

**Declare it.** An attempt that emits an unrepresentable column carries
`unrepresentable.json` beside `concept.sql`:

```json
{
  "anchor_age":  "No FHIR element. Patient.birthDate stores only (anchor_year - anchor_age); the pair is collapsed into its difference.",
  "anchor_year": "Same collapse. Approximable at ~99% via min(year(Encounter.period.start)), but not exactly, so NULL is emitted rather than an estimate."
}
```

The comparator **verifies** the declaration rather than trusting it. A declared
column that is not part of the manifest, or that holds any non-NULL value in
the candidate, is a blocking `false_unrepresentable_declaration` — in both
cases the port's claim and the port's own data contradict each other, and
there is nothing for the judge to weigh. Columns that are 100% NULL but
undeclared are reported as a note — that is the shape of a gap nobody wrote
down.

A declared column that is part of the **manifest key** is different, and does
not block. The keyed join cannot align a single row, so every count in that
diff is void — but the port did not cause it. The manifest key is chosen by
empirical uniqueness over relational MIMIC (`oracle_manifest.py`), blind to
what MIMIC-on-FHIR carries, so it can land on a column no port could supply.
The comparator marks the diff `VOID DIFF` in `notes`, and the result reaches
the **judge**, which rules on the declaration and the prober's evidence rather
than on counts that measure key selection. Blocking it here would also make
honesty the expensive option: a port that omits `unrepresentable.json`
entirely reaches the judge, so declaring the gap must not cost more than
staying silent.

`epinephrine` is the worked example. Its manifest key is
`(linkorderid, starttime)` — not because `linkorderid` is the concept's grain,
but because `(stay_id, starttime)` is not unique at full scale for this itemid
(`key_probes: 6` vs `4` for `dopamine`, `dobutamine`, `vasopressin` and
`milrinone`, which carry the identical gap and were judge-accepted). The
manifest key is comparison metadata. It is never a claim about the concept's
grain, and a port is never required to reproduce it.

A verified declaration is **evidence, not a verdict**. It never turns `review`
into `match`; it attaches the port's stated reason to the divergence so the
judge rules on a claim instead of inferring intent. Without it, a concept like
`age` reports "431,231 of 431,231 rows differing", which reads as catastrophic
until someone opens `columns_differing` and finds two all-NULL columns.

### Essential loss blocks the concept, not just a column

Column-level declarations are appropriate only when the missing information is
ancillary and the remaining result is still a faithful port of the concept.
They are not a way to publish a plausible-looking table after an input needed
by the core derivation has been lost.

An absence is **essential** when it can change row inclusion, the concept's
semantic grain, grouping, temporal carry-forward, or a clinically meaningful
derived output. If one source field collapses several source states that take
different branches in the canonical SQL, choosing the served value, the modal
state, or a mostly-correct state is an estimate, not a mapping. The whole
concept must be `BLOCKED_REPRESENTATION`; downstream concepts must not execute
against a table whose ordinary values conceal that ambiguity.

**"Semantic grain" is not the manifest key.** The manifest key is whichever
column set `oracle_manifest.py` found empirically unique first, searching
size-first through a fixed identity/time vocabulary over relational MIMIC, with
no knowledge of what MIMIC-on-FHIR carries. It is a diagnostic device for
aligning two tables, chosen for the quality of the diff it produces. A concept
whose declared unrepresentable column happens to sit in that key has **not**
thereby lost its grain, and the fact alone is not grounds for `blocked`.

Test the grain directly instead: what identifies one row of *this concept* —
usually whose it is plus when. If the representable columns still answer that,
the port is faithful and the missing identifier is ancillary. Two traps to
avoid, both observed:

- **Size-first selection.** A one-column unmappable key wins before any
  two-column mappable key is considered. `neuroblock` keyed on `orderid` at
  `key_probes: 2`, so `(stay_id, starttime)` was **never probed** — its
  uniqueness is unknown, not refuted. Never infer from the manifest key that no
  representable key exists; check `key_probes` against the candidate order.
- **Administrative identifiers are not grain.** `inputevents.orderid` and
  `linkorderid` are the source system's order numbers. Losing them does not
  make two clinical rows indistinguishable unless the representable columns
  genuinely collide, which is a measurable question, not an inference.

`epinephrine`, `norepinephrine` and `neuroblock` all reached this position,
while `dopamine`, `dobutamine`, `vasopressin` and `milrinone` — same table,
same ETL, same gap — were judge-accepted purely because their key search
stopped on `(stay_id, starttime)`. Rule on the concept, never on which column
the builder reached first.

`gcs` is the worked example. The chartevents ETL writes both `No Response` and
`No Response-ETT` as Quantity `1` and drops the source text. That distinction
changes `gcs_unable`, `gcs_verbal`, total `gcs`, and the six-hour carry-forward
logic, so it is essential. Emitting Quantity `1` for the ambiguous rows or NULL
only for `gcs_unable` would still publish semantically unreliable GCS values to
`first_day_gcs`, `sofa`, and `sapsii`. The faithful outcome is to block `gcs`
until the upstream representation preserves the discriminator.

There is deliberately **no early semantic auto-block**. The prober and
diagnostician collect evidence and may recommend that the gap is essential,
but they do not decide the terminal state. A full-data `match` and mechanical
`mismatch` come from the deterministic comparator. Every non-exact semantic
result reaches the independent judge, which alone returns `accept`, `bug`, or
`blocked`. For now, an intrinsic New York one-hour DST normalization may be
accepted when the comparator/judge proves it, and an ancillary missing field
may be accepted when the remaining table is faithful; essential loss is
`blocked`.

**The 13 unkeyed concepts get less, and the residual is paired to get it back.**
With no key to align rows, a NULL-for-value divergence lands in `only_oracle`
*and* `only_candidate` at once, indistinguishable from an invented row.

The two counts are **not** the way out of that, because they are not
independent. `EXCEPT ALL` is multiset difference, so

```
|only_oracle| - |only_candidate| == oracle_rows - candidate_rows
```

*identically*. When the row counts match the two divergence counts are equal —
for every candidate, however wrong. "Both are 3,182, so these are paired
substitutions rather than invented rows" is therefore vacuous, not merely weak.
Revised 2026-08-10, after four accepted concepts were found resting on it.

So the comparator pairs the residual explicitly: it searches for a small column
set `D` such that the two residuals are equal as multisets once `D` is projected
away. If one exists **and** the remaining columns include an identity column —
the same anchoring rule keys obey, for the same reason — the residual is "the
same rows differing in `D`", every substituted column is classified exactly as
the keyed diff would classify it, and the result carries
`classification: paired_residual`. Such a concept is then judged at whatever
tier its columns imply, like any keyed one, and reports a real
`identical_fraction`.

When no such `D` exists, or it exists but is unanchored, the rows genuinely do
not correspond. The result keeps `classification: unavailable_no_key` and routes
to `review` rather than hard-failing — failing a legitimate gap on an artifact
of the comparison method is the worse error. The judge is told it is reasoning
with less evidence, that the count equality is *not* the missing evidence, and
should treat `only_candidate` there as a bug unless the evidence positively
shows otherwise.

This matters for tiering, not just for rigour. `only_candidate` is a `contested`
class, so before pairing **every** unkeyed concept with any divergence was
forced to the raised bar and had to produce an ETL citation — including
`acei`, `arb` and `antibiotic`, whose divergence is candidate-NULL-where-the-
oracle-has-a-value and therefore textbook `gap_shaped`. They cleared a bar that
should never have been set for them.

Keys are discovered **empirically against full data**, never parsed from SQL and
never derived from demo. Two rules, both learned the hard way:

1. A key must be **anchored** by at least one identity column. On 100 demo patients
   a bare `charttime` is unique; at 300k patients it is not.
2. Demo-derived keys are unsafe. Nine of 65 disagree with full data, and for `bg`,
   `kdigo_creatinine`, `kdigo_stages` and `phenylephrine` the demo key is **not
   unique** on full data — a join on it would silently fan out.

Prefer the **smallest** unique key. If a port gets `subject_id` wrong but `hadm_id`
right, keying on `hadm_id` alone reports a value mismatch in a named column; keying
on both reports "row missing" plus "extra row", which localises nothing.

## Concurrency: waves of parallel goals

`ConversionController.start()` used to raise on any other active concept. That
invariant is gone. Any number of concepts may be `RUNNING`, `VALIDATING_DEMO`
or `VALIDATING_FULL` at the same time.

**One concept per `/goal` did not change.** A goal still receives exactly one
named concept, still never auto-advances to the next, and still runs its
subagents sequentially; one attempt still carries at most one full run.
Parallelism is composed by the human — N terminals, N goals, one concept each —
and lives entirely outside the loop. A goal that sees four other concepts
active is looking at its siblings, not at corruption. Dependency gating via
`depcheck` is unchanged.

Which concepts share a wave is a human scheduling decision taken before any
goal starts, and the rules for it live in `README.md`. Nothing inside a goal
depends on how the wave was composed, so a goal never has grounds to conclude
one was composed wrongly.

### What replaces the invariant

The single-active rule was implicitly protecting three unrelated resources at
once, at the price of never running two concepts. Each now has its own
mechanism.

| Resource | Why the invariant covered it | What covers it now |
|---|---|---|
| The local Spark JVM | one laptop, one driver heap, one `spark-warehouse/` Derby metastore in the repo root that two sessions in the same cwd collide on | an OS-level `flock` around the embedded executor — at most one local JVM, the rest block until it exits |
| The remote `mimic_utils` tree | `stage_attempt` rsynced `--delete` into one shared path, so a launch could rewrite the module tree a running job was importing | staging is per attempt: `<remote_attempt>/src/mimic_utils/`, and the code that produced a verdict is part of that attempt's evidence |
| `MIMIC_NOTES.md` | one file, edited in place, and the loop guaranteed one writer | one append-only fragment per concept under `MIMIC_NOTES.d/`, owned by exactly one goal |

### Fragments are provisional

`MIMIC_NOTES.d/<concept>.md` carries one loop's live hypotheses, written before
its own full run confirmed anything. Read a fragment as a lead to verify
against served data, never as an established fact, and never cite one as
evidence for a verdict. If `bg`'s prober writes a wrong claim, four siblings
inherit it, and the mechanism goes from saving HPC runs to multiplying one
wrong one across the wave. `MIMIC_NOTES.md` remains the curated read surface: a
human merges fragments into it by hand, and a fragment stays provisional until
that happens — which is what makes an entry in `MIMIC_NOTES.md` mean "checked"
and a fragment mean "one loop currently believes".

`carryover/<concept>/` is unaffected: it was already per-concept, and it is
still edited in place.

### Staleness replaces the liveness signal

A single `Active:` concept was doubling as a liveness detector — a dead loop
stopped the system and named itself. With five loops a stranded `chemistry`
silently blocks `creatinine_baseline`, `first_day_lab`, `sofa` and `sapsii`
through `depcheck` until someone notices weeks later, and the goal runner's
budgets make stranding the normal case rather than the exception.

So every CLI transition stamps `updated_at`, `hpc-poll` touches it on each
poll, and `mimic_utils status` renders the time since the last transition and
takes `--stale`. Thresholds: `RUNNING` 45 min, `VALIDATING_DEMO` 90 min — it
must exceed the Spark lease's 60-minute wait, or a loop queued behind the lease
reads as dead — and `VALIDATING_FULL` 15 min, which is three missed polls and
is only meaningful because the poller heartbeats.

Staleness is advisory and display-only, with one exception: `resume --apply`
and `retry` refuse on a concept that still looks live, and `--force` overrides
them. The bar for `--force` is a session you *know* is dead — never an error
you have not diagnosed.

## Gates

### Demo — cheap shape gate, NOT a correctness gate

Runs locally: **embedded Pathling on Spark** over the demo Delta warehouse,
seconds per attempt, no queue. Same engine as the full leg, deliberately — the
full leg cannot use anything else, so a demo run on a different engine would
only be predictive by luck. The HTTP Pathling server is a diagnostic fallback,
not part of the loop.

Its job is to catch the errors that do not need 156 GB to reveal:

- the ViewDefinition or SQL fails to execute at all
- returned column **names** do not match the target
- returned column **types** are incompatible
- output shape is structurally wrong

Explicitly **not** a demo gate:

- **Row count is not a demo gate.** Demo agreement is not evidence of correctness and
  demo disagreement is not proof of a bug.
- **0 rows on demo is `unsure`, never `fail`.** The 100-patient cohort legitimately
  contains nothing for some concepts. Do not fail, and do not pass — proceed to full.

A demo failure is a fast, cheap bug report. A demo pass earns nothing except
permission to spend an HPC run.

### Full data — the real correctness signal, inside the loop

Runs on HPC: Pathling/Spark over the 156 GB `spark_warehouse`, compared against the
oracle in the same job (both node-local, no data movement). ~10–30 min per run plus
queue.

- This is where correctness is decided: schema identity, and the classified keyed
  diff. Row count is reported but not gated (see above).
- The agent may submit **as many full runs as it judges necessary**, iterating on the
  diff each time.
- **Hard cap: 10 full runs per concept.** On the 10th without convergence the concept
  terminates for human review.

The full run is *not* a final one-shot confirmation of a demo-approved answer. Demo
never approves an answer; it only rejects malformed ones.

## Terminal states

| State | Reached when |
|---|---|
| `COMPLETED` | verdict `match` — nothing diverged |
| `COMPLETED_WITH_DIVERGENCE` | verdict `review` (either tier), and the divergence was accepted with a cited justification |
| `BLOCKED_REPRESENTATION` | the divergence is intrinsic **and** unacceptable, citing a specific element, path, or ETL statement |
| `FAILED` | an unresolved `mismatch`, 10 full runs without convergence, or an unrecoverable error |

`COMPLETED` and `COMPLETED_WITH_DIVERGENCE` are **reported separately and never
summed**. "N of 65 exact, M of 65 accepted with documented divergence" is a claim
the artifacts support; "N+M of 65 completed" is not.

Reaching `COMPLETED_WITH_DIVERGENCE` requires a recorded justification —
`mimic_utils accept-divergence <concept> --justification "..."` refuses without
one. For a `gap_shaped` result the justification names the FHIR element or path
that is missing; for a `contested` one it also names the upstream ETL statement.

### Manual intervention

`BLOCKED_REPRESENTATION` means the equivalence judge already returned
`blocked`, and a human must decide whether to revisit or override that ruling.
The two things a human can conclude are *try again* and *this is intrinsic and I
accept it*, so both edges exist:

```
BLOCKED_REPRESENTATION → RUNNING                     (retry)
BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE   (manual acceptance)
```

The second requires `--by human`:

```
mimic_utils accept-divergence <concept> --by human --justification "..."
```

`--by human` is the **only** way to clear a block, and it is refused on any other
route into that state. The judge was called on the preceding `review` and put
the concept into the blocked state; it is not called again to reconsider its
own ruling. Recording a later human override as the judge's would misattribute
that decision. `divergence_decided_by` is stored in `state.json` and
`mimic_utils status` reports the two counts on separate lines:

```
  N/65 exact match
  M/65 divergence accepted by the judge
  K/65 divergence accepted by a human (manual override)
```

Three lines, never summed. A human override is a real result and a weaker one:
it was decided outside the protocol, and a reader who cannot tell which is which
is being asked to trust the loop on precisely the point worth checking.

`status` also lists every active concept with the time since its last
transition, and `--stale` filters to the ones past their threshold — see
"Concurrency: waves of parallel goals" for what the thresholds mean.

The judge can never override a `mismatch`. It decides `review` results, at the
bar its tier sets.

### Reopening a finished port

Added 2026-08-11. `COMPLETED` and `COMPLETED_WITH_DIVERGENCE` were sinks, on the
reasoning that a recorded verdict is final. That is right about the verdict and
wrong about the SQL, which is a separate artifact that can turn out to be
defective after the verdict is sound — a cast idiom whose behaviour depends on
the session timezone, a construction that yields NULL where it should yield a
value. The loop had no way to express "this port is finished and its query is
wrong", so the only available move was to edit `concept.sql` inside the finished
attempt.

That move is worse than it looks. `export_mappings` reads the **current**
attempt, so the edit silently becomes the exported mapping, while
`comparison.full.json`, `run_meta.full.json` and the recorded justification stay
behind describing a query that no longer exists. Nothing in the loop hashes
`concept.sql` — only the DAG's oracle SQL and the config files are hashed — so
no artifact would ever contradict the pair, and "M of 65 accepted with
documented divergence" would quietly stop being a claim the artifacts support.

So the edge exists, and costs a full run:

```
COMPLETED                  → RUNNING   (reopen)
COMPLETED_WITH_DIVERGENCE  → RUNNING   (reopen)
```

```
mimic_utils reopen <concept> --by human --reason "..."
```

`--by human` is fixed, not defaulted: there is no agent-initiated route into
this. An orchestrator that could reopen its own finished concept could retry its
way out of any verdict it disliked, and the ten-full-run cap would bound
nothing. `retry` and `resume --apply` both refuse these two statuses and name
`reopen` instead — a flag on `retry` would have been one keystroke from
discarding a verdict by accident, which is the same reason `accept-divergence`
is not `done --with-divergence`.

Reopening **withdraws the concept as a satisfied dependency** for as long as it
is running. That is not a side effect to work around: a dependent built against
SQL now known to be defective would inherit the defect, and `depcheck` refusing
to start it is the DAG doing its job.

The superseded verdict is copied into `reopen_history` — status, justification,
decider, and the attempt/counter watermarks — and then cleared from the live
fields. A reopened concept has no verdict and earns a new one through the full
run like any other. `status` reports reopened concepts on their own line,
never summed into the other three:

```
  N/65 exact match
  M/65 divergence accepted by the judge
  K/65 divergence accepted by a human (manual override)
  J/65 reopened by a human after a recorded verdict
```

A reopened concept's final verdict is as sound as any other — it was re-earned
on full data — but the reader should know the loop was re-entered by hand rather
than converging on its own.

**Metrics are scoped per run, not per concept.** Attempt directories accumulate
across a reopen and the three state counters are cumulative, so the second run's
artifact reports attempts, judge invocations, HPC jobs and HPC seconds for
`attempt > baseline` only, where the baseline is the watermark stamped at
reopen. The first run's artifact is already written and stays correct. Cumulative
figures live under `run_scope` in the same artifact; the two are reported
separately and never summed, because a reader who cannot tell one run's cost
from a concept's total cost has a number that means neither.

### Divergent dependencies

A `COMPLETED_WITH_DIVERGENCE` concept **satisfies** the dependency check — refusing
to build on it would stall the DAG at the first accepted gap. But a concept built on
a divergent dependency *inherits* that divergence. `ConversionController.divergent_dependencies()`
lists them, and the orchestrator passes that list to the judge so it knows which part
of the gap it is assessing is not this concept's doing.

An unrepresentable column propagates the same way. Because the column is present
and NULL rather than dropped, a dependent still executes and its own comparison
classifies the inherited NULLs as `differing_null_only` — the gap stays visible
at every level instead of vanishing into a crash. A dependent that consumes such
a column **inherits the upstream declaration** and cites it rather than
re-deriving the finding; it declares the column itself only if the
unrepresentability originates in its own mapping.

`age` was expected to propagate nothing, on the reasoning that all four
consumers of `mimiciv_derived.age` — `creatinine_baseline`, `oasis`,
`charlson`, `sapsii` — select only `age` and never the anchor columns. The
anchor half of that holds. The other half does not.

The full-data run (attempt_0002, 2026-08-07) found `age` **itself** conflicting
on 460 of 431,231 rows (0.107%), because `Patient.birthDate` is synthesised
from `MIN(transfers.intime)` rather than `anchor_year` — so all four inherit a
divergence in the one column they do take. `age` is
`COMPLETED_WITH_DIVERGENCE`, accepted by a human, and
`divergent_dependencies()` will list it for every one of them.

Their judges must be told. The inherited divergence is small and intrinsic, and
it is **not** the dependent's own doing — a dependent that reports those same
460 patients as its own conflict has misattributed them.

## Data locations

| | |
|---|---|
| Full oracle | `/scratch3/nau025/oracle/mimic4-full.db` (HPC) |
| Full FHIR | `/scratch3/nau025/mimic-on-fhir-delta/spark_warehouse` (HPC, 156 GB) |
| Demo oracle | `/Users/nau025/warehouses/mimic4-demo.db` (local, read-only) |
| Demo FHIR | `/Users/nau025/warehouses/mimic-iv-demo/delta` (Delta; read by embedded Pathling on Spark) |
| Staged attempt | `/scratch3/nau025/mimic-code/mimic-iv/concepts_fhir/concepts/<category>/<concept>/attempt_NNNN/` (HPC; carries its own `src/mimic_utils/` and `oracle_manifest.full.json`) |

Every code path opens a DuckDB oracle with `read_only=True`.
