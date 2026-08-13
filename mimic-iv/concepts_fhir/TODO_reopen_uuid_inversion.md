# TODO — reopen the six concepts that invert `Observation.id`

**Status:** policy settled, reopens prepared, not executed. No warehouse rebuild
is needed. `TODO_warehouse_rebuild.md` is closed: the Sydney effect was a
read-time session-zone fluke, while the upstream New York March normalization
is real and currently irrecoverable.

**Owner:** human. `reopen` is `--by human` by construction; there is no
agent-initiated route into it.

---

## What is being withdrawn and why

Six concepts reach their verdict by reconstructing the ETL's `Observation.id`
UUIDv5 — `SHA1(UNHEX('36e18860b4aa5577bc80a5b07922cd3d') || name)` reassembled
into 8-4-4-4-12 — to detect whether an id was derived from a timestamp one hour
earlier, and to subtract that hour when it was. `code_status` does the same
thing with nine hardcoded UUID literals.

That is not a port. It inverts an undocumented implementation detail of one ETL
version; no consumer of MIMIC-on-FHIR could reproduce it; and it converts "the
served data does not carry this" into "the served data carries this, encoded in
the primary key". The verdicts it earned are real, which is exactly why it is
worth removing — the technique is invisible in the metric it optimises.

Three things changed so the next attempt does not reinvent it:

- `src/mimic_utils/sql_lint.py` refuses both constructions mechanically
  (`hardcoded-resource-id`, `resource-id-inversion`). Verify with
  `mimic_utils lint-sql <concept>` before submitting; it gates the freeze.
- `compare_port_results.py` now replays the upstream cast against the **key**,
  not only against value columns (`key_attribution`). That is what closes the
  loophole: these concepts key on `charttime`, so their DST shift showed up as
  `only_oracle` + `only_candidate` and the documented `attributed` route was
  structurally unavailable. It is available now. See LOOP_CONTRACT.md, "The
  shift can land in the key".
- `LOOP_CONTRACT.md` now makes resource/reference ids opaque identity only and
  requires the judge to block an entire concept when missing information changes
  row inclusion, keys, grouping, temporal carry-forward, or a clinically
  meaningful output. There is no agent-decided early semantic block.

---

## Current state

| concept | status | inversion | lint findings |
|---|---|---|---|
| `icp` | `COMPLETED` | algorithmic | 4 × `resource-id-inversion` |
| `height` | `COMPLETED` | algorithmic | 4 × `resource-id-inversion` |
| `crrt` | `COMPLETED` | algorithmic | 4 × `resource-id-inversion` |
| `icustay_times` | `COMPLETED` | algorithmic | 4 × `resource-id-inversion` |
| `gcs` | `COMPLETED` | algorithmic **+ value decoding** | 2 × `resource-id-inversion` |
| `code_status` | `COMPLETED_WITH_DIVERGENCE` | **nine hardcoded UUIDs** | 9 × `hardcoded-resource-id` |

Reopening withdraws each as a satisfied dependency while it runs — that is
`depcheck` doing its job, not an obstacle to work around.

---

## Order

**1. No rebuild.** The warehouse is unchanged. UTC is now pinned for reads, so
the false Sydney/October family is no longer manufactured by Spark. Only the
genuine upstream New York/March family remains.

**2. Reopen, one wave.** These six share no dependency edges with each
other, so they can run as a single human-composed wave.

**3. `gcs` and `code_status` have expected representation blocks, but the judge
still decides.** The prober and diagnostician provide evidence; neither they nor
the orchestrator may terminally block a concept before the non-exact comparison
reaches the equivalence judge.

---

## The reopen commands

Run from the repo root.

```bash
mimic_utils reopen icp --by human --reason \
  "concept.sql recomputes the ETL's Observation.id UUIDv5 (SHA1 over a hardcoded namespace) to detect and undo a one-hour DST shift. Resource ids are opaque identity, so this is not a FHIR mapping and is refused by sql_lint (resource-id-inversion). No warehouse rebuild is needed: UTC-pinned reads remove the false Sydney effect, and comparator key_attribution exposes the residual upstream New York shift as an attributed divergence without inversion."

mimic_utils reopen height --by human --reason \
  "Same Observation.id UUIDv5 inversion as icp. Refused by sql_lint (resource-id-inversion); UTC-pinned reads plus comparator key_attribution make it unnecessary."

mimic_utils reopen crrt --by human --reason \
  "Same Observation.id UUIDv5 inversion as icp, plus a REGEXP_REPLACE that guesses how the source value was stringified in order to rebuild the hash input. Refused by sql_lint (resource-id-inversion); UTC-pinned reads plus comparator key_attribution make it unnecessary. The 100% exact match was earned through an opaque-id side channel and is withdrawn."

mimic_utils reopen icustay_times --by human --reason \
  "Same Observation.id UUIDv5 inversion as icp. Refused by sql_lint (resource-id-inversion); UTC-pinned reads plus comparator key_attribution make it unnecessary."

mimic_utils reopen code_status --by human --reason \
  "concept.sql hardcodes nine literal Observation UUIDs, each mapped to an oracle timestamp read from attempt_0001's divergence report. That is evaluation-fitted row identity, not a FHIR mapping, and sql_lint refuses it (hardcoded-resource-id). The omitted POE branch changes row inclusion and must be presented to the judge as essential representation loss, not automatically re-accepted as a partial table."

mimic_utils reopen gcs --by human --reason \
  "concept.sql reconstructs the ETL's Observation.id UUIDv5 to undo a DST shift and brute-force a label vocabulary for source 'No Response-ETT'. Both uses violate the opaque-identity boundary. UTC-pinned reads plus key_attribution handle the residual New York shift; the discarded label changes core GCS outputs and carry-forward, so the reopened comparison must go to the judge for whole-concept BLOCKED_REPRESENTATION rather than a partial port."
```

---

## What each new attempt must do differently

### `icp`, `height`, `crrt`, `icustay_times`

Delete the UUID machinery outright. The query becomes what it was always meant
to be: filter by system + itemid, `TRY_CAST(effective_datetime AS TIMESTAMP_NTZ)`
(with the `Period.start` arm coalesced where the ViewDefinition projects it),
pivot, cast to the manifest types.

Any residual divergence is the upstream March DST family. Do **not** try to
recover it. It will surface as `only_oracle` + `only_candidate` on `charttime`,
`key_attribution` will pair them, and the tier lands on `attributed` with the
citation already in the artifact.

`crrt` also carries three latent issues worth fixing while it is open, none of
which affect its recorded match: text items read `string_value` only (the ETL
writes `valueString` only when `valuenum IS NULL`), an `INNER JOIN` to the ICU
encounter where a `LEFT JOIN` belongs, and a no-op `(quantity_value IS NOT NULL
OR string_value IS NOT NULL)` filter.

### `code_status`

Delete the nine literals. Keep everything else: the four categorical labels
already match the oracle character for character. The omitted POE branch has
197,931 `only_oracle` rows and no FHIR path preserving `poe`/`poe_detail`.
Because that absence changes row inclusion, it is essential under the current
contract: present the direct chart-only candidate and full-data evidence to the
judge, which should return `blocked` unless the new probe finds an exact POE
representation. Do not accept or block it at the prober/orchestrator stage.

Note that the previous evidence attributed those nine rows to the upstream
New York `TIMESTAMPTZ` cast. Five of them are October dates, which are ordinary
wall times in New York and spring-forward gaps only in `Australia/Sydney` — so
that attribution was wrong. UTC-pinned reads should make those five rows stop
diverging without changing the warehouse. If they persist, diagnose the read
path; do not paper over them.

### `gcs` — essential ETT discriminator is unmappable; judge must block

**Policy decision (human, 2026-08-13): do not publish a partial GCS table. Do
not attempt id-based recovery. The equivalence judge makes the terminal block.**

`gcs` uses the id side channel for a second thing, and timezone configuration
cannot fix it. The oracle needs the source string:

```sql
-- mimic-iv/concepts/measurement/gcs.sql:33,45
WHEN ce.itemid = 223900 AND ce.value = 'No Response-ETT' THEN 0   -- gcs_verbal
WHEN ce.itemid = 223900 AND ce.value = 'No Response-ETT' THEN 1   -- endotrachflag
```

`fhir_observation_chartevents.sql` writes `valueString` only when `valuenum IS
NULL`, so for GCS items the label is discarded and only the number survives.
`No Response` and `No Response-ETT` are therefore indistinguishable in the
served data. The current port recovers the distinction by hashing all 16
candidate labels against the resource id.

Measured on demo (`carryover/gcs/fhir-prober.md:99-113`): 3,266 verbal rows, all
with a non-NULL `valuenum`; 1,348 exact `No Response-ETT`, **every one with
`valuenum = 1`**; 78 genuine `No Response`, also `valuenum = 1`; `value_string`
populated on 0/3,266. Both labels arrive as `valueQuantity = 1`. The
discriminator is gone, and `quantity_value = 1` is not a substitute for it.

The prober reached this conclusion and then walked past it by treating an
ETL-specific UUID equality as a semantic witness. That is the failure mode this
document removes: resource identity cannot supply a discarded source value.

#### The gap is not one column

The sentinel drives three of the eight outputs:

| output | how the sentinel reaches it |
|---|---|
| `gcs_unable` | `MAX(CASE WHEN itemid=223900 AND value='No Response-ETT' THEN 1 ELSE 0 END)` — wholly determined by it |
| `gcs_verbal` | ETT rows scored `0` instead of `valuenum` (=1) |
| `gcs` | `WHEN b.gcsverbal = 0 THEN 15` — a verbal of 0 forces the score to literal 15 |

and it propagates: `COALESCE(gcsverbal, gcsverbalprev)` plus the 6-hour
self-join carry the wrong verbal forward to later rows.

This is not a column-level declaration. The missing discriminator changes three
clinically meaningful outputs and temporal carry-forward, and those values feed
`first_day_gcs`, `sofa`, and `sapsii`. A partial table would conceal ambiguity
behind ordinary numeric values. The reopened attempt exists only to produce the
non-inverting full-data comparison the judge needs; it must not be promoted.

#### The trap when the hash comes out

Deleting the UUID machinery naively collapses `endotrachflag` to
`MAX(CASE WHEN ... is_ett = 1 THEN 1 ELSE 0 END)` = **constant 0**, not NULL.
Constant 0 is the modal value — an estimate — which LOOP_CONTRACT.md forbids.
Use an explicit typed NULL in the comparison candidate; do not present that
candidate as a usable partial GCS table.

For `gcs_verbal` and total `gcs`, a candidate may expose the direct served
Quantity solely so the full diff measures the conflict. It is not a faithful
semantic value for ambiguous rows and cannot justify `accept`; the judge must
block the concept once the ETL loss and propagation are confirmed.

#### Expected magnitude — say it up front

1,348 of 3,266 verbal rows (~41%) are ETT sentinels on demo. This is not a rare
edge case. Report the full-data fidelity figures to the judge, but magnitude is
not the reason for blocking: the discriminator is essential to the derivation.

#### Worth one line upstream (not on the critical path)

Have the chartevents ETL preserve the source text unconditionally rather than
only when `valuenum IS NULL` — a second `Observation.component`, or
`valueCodeableConcept.text` beside the Quantity. That would make this concept
exactly portable. Fold into the same `mimic-on-fhir` issue as the DST cast.

---

## Verification before each submission

```bash
mimic_utils lint-sql            # sweep: every concept's current attempt must be clean
```

Zero findings across all six is the precondition for a full run. The gate runs
at the freeze transition anyway; running it by hand first just saves the trip.

### One unrelated concept the sweep also catches

`epinephrine` (`BLOCKED_REPRESENTATION`, attempt_0001) carries three
`datetime-parser` findings — the old `TRY_TO_TIMESTAMP` construction, not the id
inversion. It has no exported artifact, so the re-export that fixed the other
eight never reached it. Nothing to reopen (it is blocked, not finished), but the
SQL needs the same `TRY_CAST(... AS TIMESTAMP_NTZ)` fix whenever it is picked up,
or its next attempt will fail the gate for a reason unrelated to why it blocked.
