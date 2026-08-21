# `human_override/` — the record behind every human ruling on a judge's verdict

`LOOP_CONTRACT.md` allows exactly one transition the loop cannot make on its
own: `BLOCKED_REPRESENTATION → COMPLETED_WITH_DIVERGENCE`, by a human
(`accept-divergence <concept> --by human`, see `LOOP_CONTRACT.md:784,889`). The
judge is not re-called to reconsider its own ruling, so the override is the only
route out, and `state.json` records it in one field —
`divergence_decided_by: "human"` — plus a one-paragraph justification.

That is enough for the loop and not nearly enough for a reader. This folder
carries the argument: one file per ruling, named for the concept, written at
the time the ruling was made.

**Two document classes live here**, and the header of every file says which it
is. Most are **overrides** — a human cleared a block, and the file argues why.
A few are **block-upheld reviews** — a human re-examined a block, changed
nothing in the state machine, and recorded why it still stands. Both are human
rulings on a judge's verdict, which is what this folder is for; only the first
changes `state.json`. See "Entries that uphold a block" below.

## Rules

- **One file per ruling, named for the concept** (`antibiotic.md`).
  A second ruling on the same concept appends a new dated section rather than
  rewriting the first — the earlier reasoning is part of the record.
- **Append-only, like `MIMIC_NOTES.d`.** Never delete or silently rewrite an
  earlier section. A sharpened claim is a new section that names what it
  supersedes.
- **Every number is copied from an artifact, not remembered.** Cite the
  attempt directory and the `comparison.full.json` field it came from, so a
  reader can re-derive it.
- **Every citation is `file:line` into `mimic-fhir`**, at the statement that
  actually performs the transformation or the omission.

## Required sections

Seven, in this order. Keep each one to what it is for; the last exists so the
first six stay readable.

1. **The problem** — what is missing, on how many rows, in one short paragraph.
   Then what the judge returned and on which attempt, *quoting* its stated reason
   so the override argues against a real position rather than a paraphrase, and
   one sentence on which part of that reason is being rejected.
2. **What caused it** — the mimic-fhir ETL statement, quoted, with `file:line`.
   What it writes, what it does not, and under exactly which condition. Then the
   no-alternative-carrier check: every other element that might have carried the
   value, and why it does not.
3. **Intentional or a bug?** — ruled per class, not for the concept as a whole,
   because one statement usually produces losses of several kinds. A table is
   normally the clearest form. See the grading trap below.
4. **Example of the loss** — one real affected row, cited to the artifact it came
   from (`comparison.full.json` → `diff.samples`). Oracle values beside port
   values, plus the served resource that explains the difference. Never an
   invented row.
5. **What a fix would look like** — only for what §3 called fixable. The patched
   SQL, then the §4 example re-served under it, then the port row it would
   produce. Concrete enough that someone could open a `mimic-fhir` PR from it.
   State plainly if nothing is fixable.
6. **Numbers** — total rows, affected rows, per-column NULL counts, exact
   fidelity, and the same figures broken down by the §3 classes. Fractions stated
   as fractions. If §5 exists, the post-fix projection belongs here.
7. **Misc** — everything else, kept tight and bulleted. In practice: the
   essential-loss test of `LOOP_CONTRACT.md:481` applied term by term (row
   inclusion, semantic grain, grouping, temporal carry-forward, contamination of
   representable values); consistency with sibling concepts and with earlier
   verdicts on the same evidence; what downstream inherits; caveats; revisions to
   this file. May be empty.

**The grading trap in §3, hit on the first two entries.** "Bug" and "inherent"
are not exhaustive, and using only those two labels produces a self-contradicting
ruling. The middle case is loss the served element *could* conformantly carry,
where upstream's reason for not carrying it is a defensible judgement rather than
a mistake — typically because the source value is known to be corrupt and the ETL
declines to guess. Grade it as its own tier. Concretely: the argument that
convicts one omission as a bug ("a `Period` with only `start` is conformant")
usually also applies to a neighbouring omission ruled inherent, and an entry that
does not notice contradicts itself.

Note which way this cuts. Reclassifying loss as *repairable* does not weaken an
override — `LOOP_CONTRACT.md:256-315` makes an acknowledged, repairable
`mimic-fhir` defect the archetype for accept-rather-than-block. The override
rests on §2 and §7: nothing recoverable from what is served **today**, and an
absence that reaches nothing essential. §3 and §5 only say whether that will stay
true.

Keep §3 and §7 distinct for the same reason. "It is an upstream bug" is not by
itself a reason to accept a loss, and "no query can recover it" is not by itself a
reason to block one.

## Entries that uphold a block

Added 2026-08-21, with `ventilator_setting.md`, the first of these.

A human who re-examines a `BLOCKED_REPRESENTATION` concept can conclude *accept*
or *try again* — or **neither**: that the block stands. That third outcome moves
nothing in the state machine, so the loop records it nowhere, and until now
neither did this folder. But it is the same act of judgement as an override,
taken on the same evidence, and a reader who finds a standing condition in an
earlier entry — `gcs.md`'s "`ventilator_setting` is revisited under the same
reasoning" — needs to be able to find how it was discharged. An undocumented
re-examination is indistinguishable from one that never happened.

Such an entry keeps all seven sections and the four rules above. Four deltas:

- **The header says so, and says what did not happen.** `Decision:` states the
  block stands; `Transition applied:` states **none**, explicitly, so no reader
  infers a state change from the folder's name. Name any `state.json` field that
  *was* touched — normally at most `error_message`.
- **§1 separates the verdict from its reason.** An entry that merely agrees with
  the judge is not worth filing; the loop already recorded that. File one when
  the *reason* changes — the block survives on different grounds than the judge
  gave — and say in §1 which part of the judge's finding is being replaced and
  what replaces it. If the judge's reasoning survives intact, add a dated note to
  the concept's `state.json` justification instead of a file here.
- **§5 is not optional and is the point.** An upheld block is a standing cost.
  State what would lift it — the upstream fix, and separately any decision a
  human could take that would change the ruling without an upstream change.
- **§7 states the cost of the block.** How many concepts it gates, by name. A
  ruling that withholds work should say how much.

The grading note above inverts here, and it is worth saying out loud. For an
override, §3 grading a loss *repairable* strengthens the entry. For an upheld
block it strengthens nothing on its own: "it is an upstream bug" is not a reason
to block, any more than it is a reason to accept. An upheld block rests on §2 and
§7 exactly as an override does — on what is recoverable from what is served
**today**, and on what the absence reaches — and it must survive the possibility
that the answer to the first is "quite a lot". `ventilator_setting.md` is the
worked example: an exact reconstruction exists, which *defeats* the judge's
stated reason, and the block stands anyway because the reconstruction is not
derivable from the IG and the absence does not stay visible downstream.
