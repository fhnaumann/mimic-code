# MIMIC_NOTES.d — one append-only findings fragment per concept

`MIMIC_NOTES.md` is read-only for a running loop. Findings go here instead, in
`MIMIC_NOTES.d/<concept>.md` — one file per concept, owned by exactly one
`/goal`, so a wave of parallel loops never contends over a shared file. A human
merges the fragments into `MIMIC_NOTES.md` between waves.

## Rules

- **One file per concept, named for it.** `bg.md` belongs to the `bg` goal.
  Never write into another concept's fragment, and never write into
  `MIMIC_NOTES.md`.
- **Append only.** Add a `##` section at the end. Do not edit or delete an
  earlier section, including your own: a fragment is a running log of what this
  loop believed and when, and a sharpened claim is a new entry that says what it
  supersedes.
- **Same entry format as `MIMIC_NOTES.md`** — `##` claim heading,
  `- Affected: <resource>.<field>`, `- Verified:` naming the concept, the
  attempt number, and what was actually observed. The merge is then a copy, not
  a rewrite.
- **Dataset-wide findings only.** A quirk true regardless of concept goes here;
  what is true of this concept alone stays in the attempt's
  `evidence/<stage>.md`, and what is true of this concept across attempts goes
  in `carryover/<concept>/`.

## Fragments are PROVISIONAL

A fragment is one loop's live hypothesis, written before its own full run
confirmed anything. **Treat another concept's fragment as a lead to verify
against served data, never as an established fact, and never cite one as
evidence for a verdict.** `MIMIC_NOTES.md` has been through a full run and a
human; a fragment has not.

That distinction is the whole reason the split is safe. If `bg`'s prober writes
a wrong claim and four siblings adopt it as fact, the mechanism stops saving HPC
runs and starts multiplying one wrong run across the wave.

## Between waves

Merging is a precondition for the next wave, not a tidy-up. The next wave's
loops read `MIMIC_NOTES.md`, so an unmerged fragment is knowledge the wave will
pay an HPC run to rediscover. Merge into the existing entry where one exists —
update it rather than appending a near-duplicate — and leave the fragment in
place as provenance.
