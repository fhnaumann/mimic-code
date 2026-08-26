# MIMIC_NOTES.md — cross-concept knowledge about the MIMIC-on-FHIR data

Dataset/IG-level quirks that hold regardless of which concept is being ported.
Read this **before** probing the IG or authoring a ViewDefinition or SQL.
Concept-specific findings belong in that attempt's `evidence/<stage>.md`
instead.

Entry format: short claim · affected resource/field · one line on how it was
verified (so a future agent can trust-but-recheck cheaply).

**This file is READ-ONLY for a running loop.** Do not edit it — not to add an
entry, not to sharpen one. Write your findings to
`MIMIC_NOTES.d/<concept>.md`, the append-only fragment your `/goal` owns, in
this same entry format; the protocol is in `MIMIC_NOTES.d/README.md`. Several
goals run at once as a wave, and five loops editing one markdown file in place
lose each other's writes. A human merges the fragments back into this file
between waves, which is also what makes an entry here mean "checked", against a
fragment's "one loop currently believes".

## Provenance of the verification lines

This file was seeded from the paper-reproduction loop at
`../master_thesis_pipeline/paper_reproductions/MIMIC_NOTES.md`, so most
`Verified:` lines cite paths in *that* repo (`papers/<slug>/tmp/…`,
`common/executor.py`, paper slugs like `lin-2025`, `liu-2022`). Those are
provenance, not files in this repo — read them as "someone checked this, here is
where the check lives". Verifications you add should cite paths in **this** repo
(an attempt's `evidence/<stage>.md`, a `comparison.full.json`, a demo run) so
the trail stays followable from here.

The two files have since diverged and are **not** kept in sync automatically. If
a quirk you find is dataset-wide, it is worth carrying back there by hand.

There is a third tier, below both: `MIMIC_NOTES.d/<concept>.md`. Those
fragments are one loop's live hypotheses, written mid-run and not yet merged
here. An entry in *this* file has survived a full run and a human's read; a
fragment has not. Verify a fragment against served data before acting on it,
and never cite one as evidence for a verdict.

---

## READ FIRST — three upstream defects were FIXED on 2026-08-21; entries below may be historical

Three of the defects this file documents as properties of the served data have
been **repaired in `mimic-fhir` and the warehouses rebuilt**. Several entries
below were written while they were live, and they are kept — the artifacts of
every attempt up to 2026-08-24 argue from them, and a reader of those artifacts
needs to know what was true when they were written. But **do not port against
them**: check this table first.

| defect | fixed by | what changed | entries now historical |
|---|---|---|---|
| DST spring-forward wall times normalised +1h by a `TIMESTAMPTZ` cast | `ade10fb` (upstream #124) | the FHIR tables are now generated under **UTC**, which has no DST in any year, so the cast is an identity on the wall clock. The cast statements are still in the ETL — their line citations still resolve — but they no longer move a timestamp. | "FHIR datetimes carry an offset" (the **DST-gap** half only), "Labevents DST normalization can change dependent time-window aggregates" |
| `Patient.birthDate` synthesised from `MIN(transfers.intime)` | `3048c88` (upstream #126, #117) | `birthDate` is now `MAKE_DATE(anchor_year, 1, 1) - anchor_age`, taken from the `patients` row itself. Same element, same path, correct value, and better coverage: the old `INNER JOIN transfers` left ED-only patients with no `birthDate` at all. | "`Patient.birthDate` is NOT `anchor_year - anchor_age`" |
| `chartevents.value` discarded whenever `valuenum` was set | `e7c326b` (upstream #125) | the source text is now carried in `Observation.component`, coded with the same `mimic-chartevents-d-items` coding as `Observation.code`, wherever the text is not the number restated. `No Response` and `No Response-ETT` are distinguishable again. | "Categorical chartevents store their label in valueString" (extends it rather than replacing it) |

**Not fixed, still true.** `inputevents.linkorderid` / `orderid` are still only
inside the opaque `MedicationAdministration` UUID; the hospital `poe`/`poe_detail`
branch is still absent; `inputevents.starttime` is still dropped for non-rate
administrations (`fhir_medication_administration_icu.sql:61-69`); ICU
`MedicationAdministration` Quantity values are still served at decimal scale
six — and that one is **not an upstream defect at all**, it is Pathling's
encoder, so no `mimic-fhir` fix or rebuild will ever clear it (see "Pathling
encodes every FHIR decimal as `DECIMAL(32,6)`"). Do not read this section as
"upstream is clean now".

**What this means for a port.** The fixes to the first two change *values at
paths a port already selects*, so the same SQL simply reproduces more rows — no
re-mapping, and `mimic_utils replay` exists to re-measure those concepts without
re-authoring them. The third **adds an element**, so a port written against its
absence is now incomplete and must be re-authored; `replay` refuses those
concepts by name rather than letting a false unrepresentability declaration
through a second time.

- Affected: everything time-keyed, everything age-derived, and every numeric
  chartevents concept whose source `value` carried a distinct meaning.
- Verified: `demographics/age` attempt_0004 — the **same** `concept.sql` as
  attempt_0003, byte-identical, re-run against the rebuilt full warehouse.
  Conflicts went 504 → **0** (460 `age` + 44 `admittime` all cleared),
  `only_oracle` and `only_candidate` stayed 0, `representable_fraction` went
  0.998831 → **1.000000**, and the tier dropped `contested` → `gap_shaped` with
  only the two declared `anchor_*` typed NULLs left. That is one artifact
  confirming both the birthDate and the DST fix, on full data, with the query
  held constant.

## Extensions are not a column — use `extension(url)` in FHIRPath

Pathling's encoders do not expose an `extension` column on the resource
DataFrame; extensions are stashed in an `_extension` map keyed by the `_fid`
column. A direct `explode(extension)` fails with `UNRESOLVED_COLUMN`, which is
what a probe hunting for a MIMIC-specific field will hit first. From a
ViewDefinition the FHIRPath `extension('<url>')` function works normally:

```json
{ "path": "extension('http://hl7.org/fhir/us/core/StructureDefinition/us-core-race').extension.where(url='text').value.ofType(string).first()",
  "name": "race_text" }
```

Demo `Patient` carries exactly three extension URLs — `us-core-race` (100),
`us-core-birthsex` (100), `us-core-ethnicity` (82) — each with nested
`ombCategory` / `text` sub-extensions. Notably, **no MIMIC-specific extension
exists** on `Patient`: `anchor_age`, `anchor_year` and `anchor_year_group` are
not stashed there.

- Affected: any probe or view reading extensions, on any resource.
- Verified: 2026-08-07 probe over the demo Delta warehouse — `explode(extension)`
  errored; `explode(_extension)` and `extension(url)` in a ViewDefinition both
  returned the three URLs and resolved `race_text` (e.g. `White`).

## Code systems are mostly proprietary and flat — except Condition.code

Most fields use MIMIC's proprietary code systems: flat enumerations with no
hierarchy and no inter-code relationships. The exception is `Condition.code`,
which carries proper ICD-9-CM / ICD-10-CM codes in the served Delta.

This does not change how a port filters — the code set is always the literal
one the source SQL names (see `AGENTS.md` → Coding policy) — but it does mean a
concept expressed as "all descendants of X" has no expansion mechanism here.
MIMIC's concept SQL enumerates its codes, so this has not yet come up.

- Affected: all coded fields except `Condition.code`.
- Verified: IG variant design (see `AGENTS.md`); proprietary systems are
  registered as flat complete code lists.
- **MIMIC-IV 2.2 dropped `d_labitems.loinc_code`** — the canonical
  `buildmimic/postgres/create.sql:79-85` defines `d_labitems` with only
  `itemid/label/fluid/category`, and the demo DuckDB `DESCRIBE` agrees. Lab
  concepts (`bg`, `chemistry`, `coagulation`, …) therefore have **no relational
  LOINC mapping** in this build; lab itemids are pure proprietary codes and any
  LOINC the FHIR layer carries comes from the ETL, never from `d_labitems`.
- Verified: 2026-08-07 source analysis of `bg` — `DESCRIBE mimiciv_hosp.d_labitems`
  on the demo oracle (no `loinc_code`/`loinc_description` columns) and the v2.2
  build DDL in this repo.

## Raw `Mimic*.ndjson.gz` in the warehouse are stale — probe the Delta tables

The warehouse holds both raw `Mimic*.ndjson.gz` source files and processed Delta
resource tables (`Condition.parquet`, `Observation.parquet`, …). Only the Delta
tables are authoritative — they are what Pathling's `read.delta` serves and what
every reproduction queries. The ndjson is pre-processing and can carry different
codes/systems: e.g. `Condition.code` was re-coded from the proprietary
`mimic-diagnosis-icd9/10` systems (seen in ndjson) to proper `icd-9-cm`/
`icd-10-cm` in the served Delta (seen by the SQL).

- Affected: any code/system characterization; confirmed on `Condition.code`.
- Verified: `gzcat MimicCondition.ndjson.gz` shows `mimic-diagnosis-icd10`, while
  the served view matches `%icd-10-cm` (liu's `condition.json`). Always probe via
  the executor (Spark over delta) or code-search — never the ndjson.

## HISTORICAL (fixed 2026-08-21) — `Patient.birthDate` was `MIN(transfers.intime) - anchor_age`

**FIXED UPSTREAM.** `mimic-fhir` `3048c88` (upstream #126, #117) re-anchors
`birthDate` to `MAKE_DATE(anchor_year, 1, 1) - anchor_age`, read from the
`patients` row, and drops the `transfers` join entirely. Anchoring to Jan 1 is
deliberate: it reproduces the canonical
`anchor_age + DATETIME_DIFF(admittime, DATETIME(anchor_year,1,1), YEAR)`
exactly, and it makes the calendar-year and anniversary age computations agree,
which they do not for an arbitrary month and day. So `age` is now **exactly**
derivable from `birthDate`, and the 460-row conflict below is gone — confirmed
on full data by `age` attempt_0004 (see "READ FIRST" above).

What did **not** change: `birthDate` is still a single date, so the
`(anchor_age, anchor_year)` pair is still collapsed and neither member is
individually recoverable. A port must still emit typed NULLs for them, and
`anchor_year_group` is still not representable. The rest of this entry is the
record of the old behaviour, kept because every artifact written before
2026-08-24 argues from it.

The upstream ETL used to synthesise `birthDate` from the patient's earliest
transfer time, not from the anchor pair:
`mimic-fhir/sql/fhir_patient.sql:15` is
`CAST(CAST(MIN(tfs.intime) AS DATE) - CAST(pat.anchor_age || 'years' AS INTERVAL) AS DATE)`.

Consequences for any age computation:

- Age at a point in time is `year(event) - year(birthDate)`, which reduces to
  `anchor_age + year(event) - year(MIN(transfers.intime))`. This matches the
  canonical `anchor_age + DATETIME_DIFF(...)` **only where
  `year(MIN(transfers.intime)) == anchor_year`** — about 99.9% of rows, but
  **not 100%**.
- **Verified divergence:** full-data `age` (demographics/age, attempt_0002)
  showed 460/431,231 rows where the year-subtraction age is off — typically
  **~2 years too high** (and up to +6) for patients whose earliest transfer
  year is before the anchor year. E.g. subject 12047822: oracle pair
  `(anchor_age=91, anchor_year=2165)` implies birth year 2074, candidate family
  implies 2072. This is **not** a year-boundary bug in `YEAR()`; it is an
  intrinsic mismatch between the canonical anchor-pair age and the age the FHIR
  `birthDate` encodes.
- There is **no exact recovery**: `anchor_year`/`anchor_age` are not in FHIR,
  and re-deriving from the encounter graph `min(year(Encounter.period.start))`
  is only approximate (~99%).

So `year(event) - year(birthDate)` is the best a port can do, but a port that
emits it will show a small `differing_conflict` on the `age` column for those
~0.1% of patients. This is a representability gap of the data, not a candidate
bug.

What survives and what does not:

- **`anchor_age`, `anchor_year` individually** — not recoverable from `Patient`
  alone; only the birthDate collapse (and that collapse is itself offset to
  `MIN(transfers.intime)`, not `anchor_year`) survives. `anchor_year` is only
  approximately recoverable as `min(year(Encounter.period.start))` — a
  heuristic, not an identity.
- **`anchor_year_group`** (`2011 - 2013`, `2014 - 2016`) — **not representable**.
  It is a real-world calendar bucket, and date-shifting is precisely the
  operation that destroys the mapping from shifted year to real year. No FHIR
  element carries it and no derivation from shifted dates can recover it.

- Affected: `Patient.birthDate`; every age-derived concept (`age`,
  `creatinine_baseline`, `oasis`, `charlson`, `sapsii`).
- Verified: two ways. (a) Demo probe 2026-08-07 over the demo Delta joined to
  the DuckDB oracle — year-subtraction 275/275 exact, but this only holds
  because the 100 demo patients happen to satisfy
  `year(MIN(transfers.intime)) == anchor_year`. (b) Full-data run
  `demographics/age` attempt_0002 `comparison.full.json` — 460/431,231 rows
  `differing_conflict` on `age` (~2y high), root cause traced to
  `fhir_patient.sql:15` synthesis. The demo result over-generalised the anchor
  relation to the full cohort; trust the upstream ETL over the demo probe.

## MIMIC ids live in `identifier.value` as STRINGs — `getResourceKey()` is a UUID

Every output column named `subject_id`, `hadm_id` or `stay_id` comes from
`identifier.value`, never from `getResourceKey()` / `getReferenceKey()`. The
resource keys are UUIDs (`Patient/0a8eebfd-a352-…`); the manifest declares these
columns `INTEGER`, so a UUID lands in the shape gate as `VARCHAR` and fails it.

The four systems, all sharing the `Patient`/`Encounter` tables:

| system | value is | on |
|---|---|---|
| `http://mimic.mit.edu/fhir/mimic/identifier/patient` | `subject_id` | `Patient` |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-hosp` | `hadm_id` | `Encounter` |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu` | `stay_id` | `Encounter` |
| `http://mimic.mit.edu/fhir/mimic/identifier/encounter-ed` | an ED contact — neither | `Encounter` |

`identifier.value` is a **string** even though the digits are numeric, so the
SQL must cast: `CAST(subject_id AS INTEGER)`, `CAST(hadm_id AS INTEGER)`. The
prober reports these columns as `VARCHAR` for exactly this reason — that is the
FHIR type, not the required output type. Full recipe (ViewDefinition blocks plus
the join) in the `fhir-mapping` skill, "Identifier spine".

The resource keys are needed twice over, and both are required outputs.

They are the **join** keys between resources
(`Observation.subject.getReferenceKey(Patient)` = `Patient.getResourceKey()`),
and they are **output columns in their own right**: every identifier column a
concept emits is accompanied by the key of the resource it came off —
`subject_id`+`patient_key`, `hadm_id`+`encounter_key`, `stay_id`+
`icu_encounter_key`, `specimen_id`+`specimen_key`. The manifest declares them
per concept as `key_columns` and the shape gate fails a port that omits one.

Emit the key **uncast and verbatim**. It has no manifest type, and it is not
interchangeable with `Resource.id` — see the next entry.

- Corrected 2026-08-17. This entry previously read "project both: the UUID to
  join on, the identifier value to emit", which every port read as licence to
  drop the key at the outermost `SELECT`. All 36 were reopened to add it. The
  consumer is a downstream SQL-on-FHIR layer that joins derived tables on
  `getResourceKey()` and cannot use the integers, so an integer-only table
  joins to nothing — silently, as an empty result rather than an error. See
  `TODO_reopen_resource_keys.md`.

## `getResourceKey()` is type-prefixed; `Resource.id` is the bare UUID

`getResourceKey()` returns `Patient/0a8eebfd-a352-522e-89f0-1d4a13abdebc` — the
type-prefixed form — in **every** position, as a resource's own key and as the
value `getReferenceKey()` returns for a reference to it. That the two are byte-
identical is what makes them join, and the SQL-on-FHIR specification requires it.

`Resource.id` is the bare UUID, without the prefix. It is a different value. A
derived table keyed on it joins to nothing, and because both are `VARCHAR`
columns with the same plausible name, nothing but the value shape distinguishes
them. Never substitute `.id` for a resource key, and never strip the prefix.

- Affected: every derived table's key columns, and any downstream join onto
  `Patient.getResourceKey()`.
- Verified: 2026-08-17, synthetic Patient + Encounter through the installed
  Pathling. `getResourceKey()` on Patient returned `Patient/0a8eebfd-…` while
  `id` returned `0a8eebfd-…`; `subject.getReferenceKey(Patient)` returned the
  prefixed form; the equi-join on the two matched 1/1 rows. The shape gate now
  samples each declared key column and rejects anything not in `Type/id` form.

Resource and reference ids are opaque identity, not encoded clinical data.
They may be compared for equality to join resources, group/deduplicate one
resource, and retain provenance. Never parse them, reconstruct the ETL's UUID
algorithm, hash candidate source values, hardcode ids from a comparison report,
or use id equality to infer a timestamp, label, identifier, or other source
value. This is forbidden even when the ETL algorithm is known and the inferred
value matches every checked row: it is an implementation side channel, not a
FHIR mapping.

- Affected: `Patient.identifier`, `Encounter.identifier`; every concept whose
  output carries `subject_id`, `hadm_id` or `stay_id` — i.e. nearly all of them.
- Verified: 2026-08-07, `demographics/age` attempt_0001 — SQL executed, 275 rows,
  all 6 column names matched, `shape_fail` on exactly two columns:
  `subject_id` VARCHAR (from `getResourceKey()`) and `hadm_id` VARCHAR (from
  `identifier.value`, uncast) against `INTEGER` in the manifest. See that
  attempt's `shape.demo.json` and `carryover/age/fhir-prober.md`, which had both
  systems and the VARCHAR typing right before the SQL was written.

## Essential source loss blocks the whole derived concept

A typed-NULL declaration is appropriate for an ancillary output whose absence
does not change the meaning of the remaining table. It is not appropriate when
the missing source information changes row inclusion, a natural key, grouping,
temporal carry-forward, or a clinically meaningful derived output. In that
case, publishing the remaining ordinary values hides ambiguity from downstream
consumers; the judge must block the entire concept.

`gcs` is the concrete case. For chartevents with non-NULL `valuenum`, the ETL
writes `valueQuantity` and drops source `value`. Both `No Response` and
`No Response-ETT` therefore arrive as Quantity `1`, but the canonical SQL uses
the distinction to set `gcs_unable`, `gcs_verbal`, total `gcs`, and subsequent
six-hour carry-forward values. The resource id must not be used to recover the
discarded label. Until upstream preserves that discriminator, `gcs` is a
whole-concept representation block rather than a partial table.

The prober and diagnostician collect this evidence but do not make the terminal
decision. Exact/mechanical outcomes belong to the deterministic comparator;
every non-exact semantic outcome belongs to the independent equivalence judge.
Ancillary gaps may still be accepted explicitly, and the irrecoverable one-hour
New York DST normalization is accepted when proven — including its second-order
effects through the concept's own SQL, and including where those change row
inclusion or timing. Unlike the `gcs` discriminator, the shift is an
acknowledged upstream defect awaiting repair rather than information the IG
cannot carry, so it is outside the essential-loss test and is never grounds for
a block on its own.

- Affected: every resource id; every concept whose core derivation consumes a
  source field omitted or many-to-one transformed by MIMIC-on-FHIR.
- Verified: policy adopted 2026-08-13 after auditing the six completed ports
  that reconstructed or hardcoded `Observation.id`; the GCS source branches are
  `mimic-iv/concepts/measurement/gcs.sql:33,45,62-95`, and the text-dropping ETL
  branch is `mimic-fhir/sql/fhir_observation_chartevents.sql:69-80`.

## Some fields are always null

Certain fields in the data are never populated and are useless to project or
filter on. List specific fields here as they are found:

- (none recorded yet — add `Resource.field` bullets with how you checked)

## Spark requires a length for VARCHAR casts

Spark 4.0.2 rejects `CAST(value AS VARCHAR)` with `DATATYPE_MISSING_SIZE`;
string outputs whose manifest type is `VARCHAR` must use a bounded cast such as
`VARCHAR(255)`.

- Affected: every `concept.sql` outer cast of a manifest `VARCHAR` column.
- Verified: 2026-08-08 acei attempt_0002 demo run — Spark rejected
  `CAST(m.drug_name AS VARCHAR)` before executing the query.

## Polymorphic fields mix datatypes across rows — COALESCE them

Some polymorphic (choice-type) fields are populated as one datatype for some
rows and another datatype for other rows. The ViewDefinition must carry *both*
variants via `ofType()`, each under its own alias, and the SQL `COALESCE`s
them; projecting or filtering on a single variant silently drops rows.

Concrete cases: `MedicationAdministration.effective` is sometimes
`effective.ofType(dateTime)` and sometimes `effective.ofType(Period).start`;
`Procedure.performed` likewise splits across `performed.ofType(dateTime)` and
`performed.ofType(Period).start` (~1982 vs ~1468 rows in the demo). Project both
variants and `COALESCE` them.

- Affected: choice-type fields; confirmed on `MedicationAdministration.effective`
  and `Procedure.performed`.
- Verified: observed during paper probes (lin-2025 `tmp/probe_verify.py` for
  `Procedure.performed`); recheck any other choice-type field with a `tmp/` probe
  before relying on a single variant.

## Quantity.value ViewDefinition aliases materialize as VARCHAR

FHIR `Quantity.value` is a decimal, but Pathling's materialized
`(value).ofType(Quantity).value` ViewDefinition column is string-like and must
be cast before numeric pivots or output. The raw encoded `valueQuantity.value`
field remains a decimal.

- Affected: `Observation.value.ofType(Quantity).value` in materialized
  ViewDefinitions.
- Verified: 2026-08-07 fresh embedded Pathling probe for `bg` — raw
  `Observation.valueQuantity.value` was `DecimalType(32,6)`, while the lab and
  chart ViewDefinition aliases were `string`; 22,957 targeted Quantity values
  were present and all required numeric casting.

## Medication name codings can have null display but readable code

Hospital-stream `MedicationAdministration.medication` codings using
`mimic-medication-name` commonly leave `Coding.display` null, but `Coding.code`
itself contains the human-readable drug name (for example `Warfarin`,
`Enoxaparin Sodium`, and `Apixaban`). Filter the code, not the display; a
display-only search silently misses these administrations.

- Affected: `MedicationAdministration.medication.ofType(CodeableConcept).coding`.
- Verified: lin-2025 `tmp/probe_anticoagulants.py` on the demo Delta tables;
  matching name-system codes were populated while their displays were null.

## Prescription Medication.code prefers NDC/formulary; the source drug name is in an identifier

Medication resources generated from `prescriptions` choose `Medication.code.coding`
by priority (NDC, then formulary drug code, then drug name). The original free-text
`prescriptions.drug` is preserved separately as
`Medication.identifier.where(system='http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name').value`.
Prescription concepts must filter that identifier value rather than assuming
`Medication.code.coding.code` is the source drug name.

For a `pharmacy_id` containing multiple prescription rows, however, the
`MedicationRequest.medicationReference` points to a medication-mix resource.
The mix has one identifier with system
`http://mimic.mit.edu/fhir/mimic/identifier/medication-mix`; each source drug
instead survives as a repeated `Medication.ingredient.itemReference` to a
component Medication carrying the name identifier above. A prescription port
must handle both the direct component reference and the mix-to-ingredient
reference, and must preserve ingredient multiplicity.

The source `prescriptions.drug_type` is not retained as a FHIR element. The
mix ETL uses it only to order ingredients (`MAIN`/`BASE`/`ADDITIVE`); neither
`Medication.ingredient` nor `MedicationRequest` carries the type, so a source
filter such as `drug_type NOT IN ('BASE')` is not exactly recoverable from the
served resources.

- Affected: `Medication.code`, `Medication.identifier`, `Medication.ingredient`,
  `MedicationRequest.medicationReference`, and the absent `prescriptions.drug_type`
  for hospital prescriptions.
- Verified: `mimic-fhir/sql/medication/medication_prescriptions.sql:19-54`,
  `mimic-fhir/sql/medication/medication_mix.sql:21-35,80-84`, and
  the 2026-08-08 embedded-Pathling probe recorded in
  `carryover/acei/fhir-prober.md`: 1,480 prescription Medication resources
  had one name identifier each; their code systems were 1,402 NDC, 72
  formulary, and 6 name. The same probe confirmed the exact mix identifier
  system and authorable path `ingredient.itemReference.getReferenceKey(Medication)`:
  314 mix resources materialized 634/634 populated component references
  (310 resources × 2 ingredients, 2 × 3, 2 × 4), all 634 resolving to exact
  source drug strings. Full-data `acei` attempt_0003 sharpened the mix branch:
  top-level-name filtering reproduced all 33 exact drug strings but missed
  186/776 `Enalaprilat` rows, exactly the 186 distinct two-row pharmacy
  groups. `mimic-fhir/sql/medication/medication_mix.sql:27-53,80-84` preserves
  those rows as ingredient references, so that omission is recoverable. The
  antibiotic probe additionally found no `drug_type` field in the served
  Medication/MedicationRequest schemas; the demo source had 3,677 BASE rows,
  but zero BASE rows matching its antibiotic name fragments.

## Prescription route and Medication code displays are null

The served prescription Medication `code.coding.display` and
MedicationRequest dosage-route `coding.display` are not populated. Filter and
join on `system` and `code`; do not depend on display text.

- Affected: `Medication.code.coding.display` and
  `MedicationRequest.dosageInstruction.route.coding.display`.
- Verified: 2026-08-08 embedded-Pathling probe over the demo Delta — code
  codings were 1,480/1,480 with `display` 0/1,480, and route codings were
  15,219/15,219 with `display` 0/15,219.

## MedicationRequest omits invalid or incomplete prescription validity periods

The FHIR ETL writes `MedicationRequest.dispenseRequest.validityPeriod` only when
both prescription times are present and start is no later than stop. Source
`prescriptions.starttime`/`stoptime` values in invalid or incomplete intervals
are therefore not recoverable from the served request; `authoredOn` is not a
substitute for either source time.

- Affected: `MedicationRequest.dispenseRequest.validityPeriod.start` and `.end`.
- Verified: `mimic-fhir/sql/fhir_medication_request.sql:172-177` and the
  2026-08-08 demo DuckDB/Delta probe: 15,225 pharmacy-linked requests had
  validity times on 14,574; the 651 omissions were 637 pharmacy groups with
  `starttime > stoptime` and 14 groups with a NULL source time. Full-data
  `acei` attempt_0003 confirmed the same transform: the source has 9,050
  invalid and 9 incomplete ACEI intervals; 9,034 currently included requests
  appeared as candidate NULL/NULL tuples, while 25 invalid intervals belonged
  to the separately missed medication-mix branch. Full-data `antibiotic`
  attempt_0001 sharpened the count on a complete direct-plus-mix port: 43,453
  candidate-only NULL `starttime`/`stoptime`/`stay_id` tuples matched exactly by
  `(subject_id, hadm_id, antibiotic, route)` and multiplicity to 43,453
  oracle-only omitted intervals (43,338 reversed and 115 one-sided-NULL).
- Verified: full-data `acei` attempt_0006 independently confirmed 9,059
  paired `differing_null_only` endpoint rows and 7 additional endpoint
  conflicts exhaustively attributed to the `TIMESTAMPTZ` cast at
  `mimic-fhir/sql/fhir_medication_request.sql:43-44`; the direct-plus-mix
  candidate preserved all 112,014 rows.


## FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ, never to TIMESTAMP

Datetimes come back as ISO-8601 strings with a `T` separator and an offset
(e.g. `2154-05-02T15:55:21-04:00`, EDT/EST varying row by row). Spark's default
parser throws on them, so a cast is required — but the obvious cast is wrong.
**Use `CAST(col AS TIMESTAMP_NTZ)`.**

`to_timestamp(col, "yyyy-MM-dd'T'HH:mm:ssXXX")` — the idiom this entry used to
mandate — parses the offset and then re-renders the instant in
`spark.sql.session.timeZone`, which defaults to the machine's local zone. On a
Sydney laptop every MIMIC timestamp shifts 13–16 hours and **0%** match the
oracle. It round-trips only when the session zone is exactly
`America/New_York`. MIMIC timestamps are de-identified wall-clock values, not
real instants, so the offset carries nothing worth preserving — discard it
rather than convert it.

`TIMESTAMP_NTZ` also beats the `substr(col,1,19)` workaround, which truncates
fractional seconds and **throws** (`CANNOT_PARSE_TIMESTAMP`) on date-only
values, aborting the run. The cast handles every shape the IG emits:

| input | `CAST(… AS TIMESTAMP_NTZ)` | `to_timestamp(substr(…,1,19), fmt)` |
|---|---|---|
| `2154-05-02T15:55:21-04:00` | `2154-05-02 15:55:21` | `2154-05-02 15:55:21` |
| `2154-05-02T15:55:21.123-04:00` | `2154-05-02 15:55:21.123` | `2154-05-02 15:55:21` (truncated) |
| `2154-05-02T15:55:21Z` | `2154-05-02 15:55:21` | `2154-05-02 15:55:21` |
| `2154-05-02` | `2154-05-02 00:00:00` | **throws** |

Use `TRY_CAST` if a malformed value should yield NULL instead of failing the
run. This matters across legs: the demo runs on a local machine and the full
run on Petrichor, so an offset-aware cast can make one concept produce two
different answers on the two engines.

- Affected: every datetime column in every view, both engines.
- Verified: 2026-08-07 probe over the demo Delta warehouse — 275 hosp Encounter
  `period.start` vs `mimiciv_hosp.admissions.admittime` in the DuckDB oracle.
  `CAST(… AS TIMESTAMP_NTZ)` 275/275 at session tz `Australia/Sydney` and `UTC`
  alike; offset-aware `to_timestamp` 0/275 at both, 275/275 only at
  `America/New_York`. Supersedes the liu-2022 note
  (`papers/liu-2022-lar-pancreatitis/NOTES.md`), which recorded the parse
  requirement but not the timezone conversion.

**DST-gap timestamps WERE irreversibly shifted +1 hour — FIXED 2026-08-21.**
`mimic-fhir` `ade10fb` (upstream #124) generates the FHIR tables under UTC, and
UTC has no DST in any year, so there is no gap for a wall time to be normalised
into. The `TIMESTAMPTZ` casts are still in the ETL and every line citation below
still resolves — but on the rebuilt warehouses they no longer move a timestamp,
and a port that reproduces a shifted value now has a bug rather than an
attributed divergence. The rest of this entry, and the propagation analysis
under it, is the record of the old behaviour: it is what the pre-2026-08-24
artifacts argue from, and it is still the right analysis of *how* a moved wall
time damages a concept, should the pin ever come off. The cast advice above —
`TIMESTAMP_NTZ`, never `TIMESTAMP` — is unaffected and still mandatory: the
offsets are still in the served strings.

Historically: the upstream ETL
cast naive MIMIC `admittime` through `TIMESTAMPTZ` (`mimic-fhir/sql/fhir_encounter.sql:65`),
and a wall-clock time that falls in the DST spring-forward gap (e.g. the
nonexistent 02:10 on a March Sunday) is normalised to 03:10 before it is
written to `Encounter.period.start`. The original 02:10 cannot be recovered — a
`CAST(period.start AS TIMESTAMP_NTZ)` faithfully preserves the already-shifted
03:10. So a full-data port comparing `period.start` to the oracle `admittime`
shows a small `differing_conflict` of exactly +1 hour on those rows (44/431,231
hosp admissions). This is a data-IG transformation loss, not a port bug.

- Affected: `Encounter.period.start`, `Observation.effective[x]`, and any
  upstream-timestamptz-cast datetime when compared value-exactly to the oracle.
- Verified: full-data `demographics/age` attempt_0002 `comparison.full.json` —
  44/431,231 rows `admittime` `differing_conflict`, always +1h (03:10 vs 02:10);
  root cause traced to `fhir_encounter.sql:65`. A fresh 2026-08-07 embedded
  `bg` probe found two ICU SpO2 timestamp collisions: source 02:00 rows for
  subjects 10003400 and 10035631 were written at FHIR 03:00, so the target
  chart stream had 15,286 rows but only 15,284 distinct
  `(subject_id,itemid,effective_datetime)` keys. Full-data `acei` attempt_0003
  found 14 further tuple conflicts from the same operation on prescription
  times: `mimic-fhir/sql/fhir_medication_request.sql:43-44` casts both
  coalesced validity endpoints through `TIMESTAMPTZ`, rewriting a source 02:00
  endpoint to 03:00 before the FHIR period is written. Full-data `antibiotic`
  attempt_0001 confirmed 123 more prescription tuples from those same lines:
  73 had start only, 46 end only, and 4 both endpoints shifted exactly +1 hour;
  ICU `stay_id` agreed on all 123 paired tuples.

**The shift also reaches `chartevents`, and its damage compounds through the
concept's own SQL.** Merged from `MIMIC_NOTES.d/rrt.md` on 2026-08-14. The same
cast at `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67` normalises
spring-forward chart times before `Observation.effectiveDateTime` is written,
and the sibling ICU statements do the same for
`fhir_medication_administration_icu.sql:8-9,61-69` and
`fhir_procedure_icu.sql:10-11,73-75`. Downstream of that, a concept that
deduplicates, groups, or overlays intervals on the shifted time turns **one**
moved source row into several divergence rows at once — the row can collapse
onto a key the candidate already holds, gain or lose partners in a range join,
or change an aggregate. So the `only_oracle` and `only_candidate` counts do
**not** balance, and their inequality is not evidence of an invented or missing
row.

- Affected: `Observation.effectiveDateTime` from `mimiciv_icu.chartevents`,
  ICU `MedicationAdministration` effective `Period` endpoints, ICU `Procedure`
  performed `Period` endpoints; and any concept keying, deduplicating or
  interval-joining on those times.
- Verified: `rrt` attempt_0001 full comparison — 821 `only_oracle` against 241
  `only_candidate` (row delta -580) on an unkeyed concept, every sampled
  `only_candidate` time a March 03:xx and the sampled `only_oracle` partners
  March 02:xx. Full-oracle replay found 608 selected chartevents source rows
  changed by `CAST(charttime AS TIMESTAMPTZ)`, accounting for all 241
  `only_candidate` and 449 of the 821 `only_oracle`; the propagation path is the
  `UNION DISTINCT` and the `LEFT JOIN ... BETWEEN` overlay at
  `mimic-iv/concepts/treatment/rrt.sql:316-326`. The original wall time is in no
  FHIR element and resource identity is opaque, so it is not recoverable by any
  query. A separate `oxygen_delivery` finding confirms the collision half:
  34 `only_oracle`, 31 `only_candidate` and 3 `differing_conflict` rows, all
   inside one 02:00–03:00 hour on the second Sunday in March, of which 31
   re-paired and 3 landed on keys the candidate already held.

- Verified: full-data `phenylephrine` attempt_0003 independently replayed the
  ICU MedicationAdministration effective-time cast. Forty-seven selected
  source rows across 19 stays were shifted (30 start endpoints and 29 end
  endpoints); the comparator attributed 46 direct conflicts and the remaining
  apparent conflicts closed under stay-plus-replayed-endpoint alignment. The
  source wall times are absent from FHIR.

## Encounter has three identifier systems — class discriminates none of them

Encounter streams are separated **only** by `identifier.system`:
`.../encounter-hosp` (275 in demo), `.../encounter-icu` (140),
`.../encounter-ed` (222). `Encounter.class` is useless as a discriminator —
ICU is `ACUTE`, but hosp splits across `EMER` (119), `OBSENC` (82), `AMB` (56)
and `SS` (18), and ED is also `EMER`. So `class = 'EMER'` mixes hosp and ED.

Hospital-admission concepts must filter `identifier.system` to
`.../encounter-hosp`: unfiltered, the Encounter table is 637 rows against 275
`mimiciv_hosp.admissions`. `partOf` links a child stay to its parent hospital
admission — 140/140 for ICU, but only 172/222 for ED, so an inner join through
`partOf` silently drops a quarter of ED encounters.

The identifier that selects the stream also *carries* the id — see "MIMIC ids
live in `identifier.value` as STRINGs" for the value side and its casts.

- Affected: `Encounter.identifier.system`, `Encounter.class`, `Encounter.partOf`.
- Verified: 2026-08-07 probe over the demo Delta warehouse — the three systems
  × class cross-tab above, and hosp Encounters joining 275/275 to demo
  `admissions` on `hadm_id`. Extends
  `papers/liu-2022-lar-pancreatitis/tmp/e2_icu_encounter_structure.py`, which
  recorded the 275/140/222 split but not the class breakdown or the ED
  `partOf` gap.

## Microbiology positivity links through micro-test, not micro-org

A culture is split across `Observation` profiles. `mimic-observation-micro-test`
(the ordered test) carries `specimen` (→ `Specimen.type`, the site: SPUTUM,
BRONCHOALVEOLAR LAVAGE, BLOOD CULTURE, URINE, …) **and** `hasMember` (→ the
organisms). `mimic-observation-micro-org` (an organism grown = a positive result)
carries **neither** a specimen reference nor its own usable back-link — reach it
only through the test's `hasMember`. So "positive culture of specimen type X" = a
micro-test whose `Specimen.type` is X **and** whose `hasMember` resolves to a
non-`CANCELLED` micro-org. Specimen type lives on `Specimen.type.coding.code`
(e.g. `70062` SPUTUM, `70021` BRONCHOALVEOLAR LAVAGE); many blood/urine specimens
have a bare `type.coding` with null display.

- Affected: `Observation` micro-test / micro-org profiles; `Specimen.type`.
- Verified: lin-2025 `tmp/probe_micro.py` + `probe_micro2.py` (micro-org
  `specimen` 0% populated; micro-test `hasMember` count == micro-org count == 338).

## Observation subtype profile metadata is warehouse-version dependent — discriminate with base bindings

The Observation `meta.profile` representation is not stable across the
MIMIC-on-FHIR warehouse variants. The embedded demo Delta currently retains
the subtype URLs (for example, `mimic-observation-labevents` and
`mimic-observation-chartevents`), while an earlier modified/merged Delta
variant assigned every Observation
`https://felix.masters/fhir/StructureDefinition/observation-merged` and removed
the original subtype URLs. ViewDefinitions must therefore discriminate with
the base-profile binding in `code.coding.system`/code, not with `meta.profile`.
For microbiology those binding systems are
`.../mimic-microbiology-test` and `.../mimic-microbiology-organism`.

- Affected: subtype-specific `Observation` views over any warehouse variant.
- Verified: 2026-08-07 embedded Pathling probe over the authoritative demo Delta:
  all 107,727 `mimic-d-labitems` rows and the 668,862
  `mimic-chartevents-d-items` rows retained their corresponding base profile;
  the prior merged result is recorded by the earlier lin-2025 probe. The probe
  and target counts are recorded in `carryover/bg/fhir-prober.md`.

## Lab Observation.specimen preserves the source specimen identifier

Every lab Observation has a `specimen` reference that joins by
`specimen.getReferenceKey(Specimen)` to a `Specimen` whose
`identifier.where(system='http://mimic.mit.edu/fhir/mimic/identifier/specimen-lab').value`
is the relational `labevents.specimen_id` as a string. This is the grouping
spine for lab pivots; do not group blood-gas Observations by patient and time.

- Affected: `Observation.specimen` for `mimic-observation-labevents` and
  `Specimen.identifier`.
- Verified: 2026-08-07 embedded Pathling probe over the demo Delta — all
  107,727 lab Observations had a non-null specimen reference and a matching
  lab Specimen identifier (107,727/107,727); the bg target's specimen/item
  join agreed with DuckDB for 8,706/8,706 rows.

## Categorical chartevents store their label in valueString

Menu/text `mimic-observation-chartevents` items keep their selected label in
`Observation.value` as a **string** (`value.ofType(string)`), not a
CodeableConcept. E.g. O2 Delivery Device (`226732`) values are strings —
`Nasal cannula`, `Endotracheal tube`, `High flow nasal cannula`, `High flow neb`.
Project `value.ofType(string)` and match the text; `value.ofType(CodeableConcept)`
returns nothing.

**Since 2026-08-21 a numeric row can carry its label too.** `e7c326b` (upstream
#125) added `Observation.component` for rows where `valuenum` **is** set and the
source `value` text is not the number restated — coded with the same
`mimic-chartevents-d-items` coding as `Observation.code`, value in
`component.valueString`. So the rule is now: `value.ofType(string)` for rows
with no `valuenum`, and
`component.where(code.coding.code = '<itemid>').valueString` for numeric rows
whose text meant something else. That is what makes `No Response` and
`No Response-ETT` (both `valuenum` 1 under itemid `223900`) distinguishable, and
what unblocks the ventilator mode/type text under `223849`/`223848`/`229314`.
The component is deliberately absent where the text is just the number as a
string, so treat it as `forEachOrNull` and expect it on a minority of rows.

- Affected: categorical `mimic-observation-chartevents` items; and, since
  2026-08-21, numeric chartevents whose source `value` carried a distinct
  meaning.
- Verified: lin-2025 `tmp/probe_data2.py` (226732 value_cc empty; value_str
  populated). The component branch is read from the ETL source
  (`mimic-fhir/sql/fhir_observation_chartevents.sql:97-113`, guarded by the
  numeric-pattern `CASE` at `:99-101`) and has **not** yet been probed against
  the rebuilt warehouse — the first port that needs it should confirm it and
  record the count here.

## ICU body temperature is split across Fahrenheit and Celsius chartevents

Numeric ICU body temperature is charted under `mimic-chartevents-d-items`
`223761` (Temperature Fahrenheit, unit `°F`) and `223762` (Temperature Celsius,
unit `°C`). Convert Fahrenheit with `(value - 32) / 1.8` and apply the official
MIMIC vital-sign plausibility limits (`70 < °F < 120`; `10 < °C < 50`) before
aggregating; the demo includes an impossible value of `99 °C` that otherwise
becomes the maximum. Observation effective time and ICU Encounter reference were
populated for every candidate demo row.

- Affected: numeric ICU body-temperature `Observation` chartevents.
- Verified: code-search exact matches plus Zhao 2024
  `tmp/probe_temperature.py` on the served demo Delta table; limits cross-checked
  against the official MIMIC-IV `measurement/vitalsign.sql` derivation.

## HISTORICAL — prod Pathling's SQL table namespace (no longer applies here)

**Does not affect any port.** The concept-port loop has no HTTP Pathling server:
both legs run embedded Pathling on Spark, where a ViewDefinition label is bound
by `createOrReplaceTempView`. Nothing below can gate a concept. It is kept only
because it backs a filed IG-conformance defect.

The prod server (`https://pathling.dw.csiro.au/fhir`) has no ambient SQL table
namespace: a table exists for `$sqlquery-run` / `$sqlquery-export` only when
declared via a SQLQuery Library's `relatedArtifact` (`type=depends-on`) pointing
at a PUT-registered ViewDefinition or sql-view Library by canonical `url`, with
`label` as the SQL table name. Inline shapes do not work — `contained`
ViewDefinitions → 400/404, and the IG's inline `view.viewResource` export param
is parsed but never materialized → 400 "SQL references an undeclared table".

- Affected: nothing in this repo. An IG/server-conformance finding, not a data
  quirk. Do not let it suggest a server mode exists to fall back to.
- Verified: live 2026-07-20; Bruno collection in `pathling_bug_report/` plus
  Python `requests` probes under `tmp/` — `tmp/verify_mixed_deps.py` confirmed
  the mixed VD+Library case (VD over Patient → 299712 rows, constant sql-view →
  1 row, both in one 200 response) and that the server binds the table name off
  `label`.

## `patient_sofa` derived table — struct columns, native timestamp

The executor mounts a non-FHIR `patient_sofa` Delta table (`common/executor.py`
`DERIVED_TABLE_VIEWS`) that the sepsis papers query for Sepsis-3 / oxygenation.
Columns: `patient_id` (`Patient/<uuid>`), `evaluation_time` (a **native Spark
timestamp** — do NOT `to_timestamp` it), `sofa_total` (worst-in-prior-24h absolute
SOFA), and two struct columns — `components` (`respiratory`, `coagulation`,
`liver`, `cardiovascular`, `neurological`, `renal`) and `worst_values` (`pao2`,
`fio2`, `pf_ratio`, `platelets`, `bilirubin`, `map`, `gcs_total`, `creatinine`).
Access nested fields as `worst_values.pf_ratio`. `pf_ratio` needs a paired
PaO2+FiO2 so it is populated for only ~55% of demo patients.

- Verified: lin-2025 `tmp/probe_data.py` + `probe_data2.py` (17,366 rows / 100 demo
  patients; 7,082 rows carry a non-null `pf_ratio`).
- **Scope in this repo:** `patient_sofa` is mounted by the paper-reproduction
  executor, **not** by this loop's demo or full runner. A concept port never has
  this table available — port SOFA from its own concept SQL. Kept here because it
  documents how that derived table was built from the same warehouse.

## Encounter diagnosis backbones are empty — join diagnoses from Condition

The served MIMIC Encounter resources do not populate `reasonCode` or the
`diagnosis` backbone (`condition`, `use`, or `rank`). Encounter-linked diagnoses
instead live as `Condition` resources with `Condition.encounter` populated and a
single `encounter-diagnosis` category. Those Conditions have no usable
`onset[x]`, `recordedDate`, clinical status, or verification status, so the
conversion cannot distinguish present-on-admission diagnoses from diagnoses
assigned later in the same hospitalization.

- Affected: `Encounter.reasonCode`, `Encounter.diagnosis`, and diagnosis timing
  or status fields on `Condition`.
- Verified: guo-wei-2024 `tmp/probe_encounter_condition.py` on the served demo
  Delta tables (0/637 Encounters with reason or diagnosis data; 5,051/5,051
  Conditions linked to an Encounter, but 0 with onset or recorded date).

## Lab Observation encounter references are incomplete — join by patient and time

Laboratory `Observation.effective[x]` is reliably populated, but
`Observation.encounter` is not. Admission-window laboratory gates should therefore
attach exact analyte codes by patient plus effective-time window; requiring an
Encounter reference silently drops valid measurements.

**For a derived-table port the consequence is sharper than for a cohort gate.**
Most lab-sourced concepts (`chemistry`, `complete_blood_count`, `coagulation`,
`enzyme`, `blood_differential`, `cardiac_marker`, `inflammation`, `bg`) select
`hadm_id` as an *output column*, and relational `labevents.hadm_id` is populated
by admission-window overlap — independently of whether the FHIR ETL wrote an
`Observation.encounter` reference. So two things follow, and they are different:

1. **Always `LEFT JOIN` to Encounter, never `INNER JOIN`.** An inner join drops
   the row entirely, turning a NULL column into a missing row and a
   `differing_null_only` gap into an `only_oracle` one.
2. **Expect `hadm_id` to be NULL in the candidate where the oracle holds a
   value**, and expect it to be a real divergence rather than a port bug. There
   is no FHIR path that recovers it: patient-plus-time re-derivation against
   hospital `Encounter.period` is a heuristic and can be ambiguous, so it is an
   estimate, not an inversion — emitting it manufactures a `differing_conflict`
   where a typed NULL would have been `gap_shaped` (see the unrepresentable-column
   rule in `LOOP_CONTRACT.md`).

**Measure the gap per concept; it does not generalise.** In `bg` the two
populations coincided — all 682 targeted lab Observations lacking an Encounter
reference were exactly the rows whose source `hadm_id` was already NULL, so the
port lost nothing. The albumin and anion-gap figures below show that is *not* the
general case. Probe the specific itemids rather than assuming either outcome.

- Affected: labevent `Observation.encounter` and `effective.ofType(dateTime)`;
  the `hadm_id` output column of every lab-sourced derived concept.
- Verified: Jian 2023 `tmp/probe_cohort.py` on served demo Delta tables: all
  albumin `50862` (625/625) and anion-gap `50868` (2,860/2,860) rows had effective
  time, while only 342/625 and 2,336/2,860 respectively had an Encounter reference;
  consistent with Liu 2022's lactate/albumin probe. Sharpened 2026-08-10 with the
  derived-table consequence from `carryover/bg/fhir-prober.md`, whose demo probe
  found 8,024/8,706 targeted lab Observations carrying an Encounter reference and
  the 682 remainder matching source-NULL `hadm_id` exactly — the coincidence that
  does not generalise.

## Lab Observation.valueString can contain the comments fallback, not source value

When a lab row has neither a numeric value nor a source text value, the upstream
FHIR ETL may populate `Observation.valueString` from the source comments field.
That fallback is not equivalent to relational `labevents.value`; ports that
reproduce a source text column must preserve the distinction (for example,
`___` is a comment marker, not a specimen value).

- Affected: `Observation.valueString` for `mimic-observation-labevents`, especially code `52033` specimen rows.
- Verified: full-data `bg` attempt_0003 diagnosis found one `52033` row with `labevents.value=NULL`, `comments='___'`, and candidate-only `specimen='___'`; upstream `mimic-fhir/sql/fhir_observation_labevents.sql:133-136` supplies the comments fallback.

## Blood glucose spans laboratory and ICU chart streams

Numeric blood-glucose measurements occur under laboratory d-labitems `50809`
(blood gas glucose) and `50931` (chemistry glucose), and ICU chart d-items `220621`
(serum), `225664` (finger stick), and `226537` (whole blood). Laboratory item
`51478` is urine glucose; similarly named ascites, pleural, body-fluid, and CSF
items are not blood glucose. All demo rows for the five blood items had
`Observation.effective.ofType(dateTime)`; laboratory Encounter references were
incomplete, so admission windows should join by patient and effective time.

- Affected: glucose-coded `Observation.code`, `effective[x]`, and `encounter`.
- Verified: He 2026 `tmp/probe_mapping.py` on the served demo Delta table; exact
  code/display/unit counts separated blood items from urine and body-fluid items.

## `Observation.code.coding.code` is the source itemid, verbatim

Every itemid-derived `Observation` stream writes the relational item id
unchanged: the ETL does `CAST(itemid AS TEXT)` and joins `d_labitems`/`d_items`
**only** for `display`. There is no padding, prefixing, or label substitution
anywhere, so `CAST(code AS INTEGER)` recovers the source itemid exactly and a
port needs no code mapping of any kind.

| ETL stream | relational column | `code.coding.system` |
|---|---|---|
| labevents | `mimiciv_hosp.labevents.itemid` | `…/CodeSystem/mimic-d-labitems` |
| chartevents | `mimiciv_icu.chartevents.itemid` | `…/CodeSystem/mimic-chartevents-d-items` |
| outputevents | `mimiciv_icu.outputevents.itemid` | `…/CodeSystem/mimic-d-items` |
| datetimeevents | `mimiciv_icu.datetimeevents.itemid` | `…/CodeSystem/mimic-d-items` |
| micro-org | `microbiologyevents.org_itemid` | `…/CodeSystem/mimic-microbiology-organism` |
| micro-susc | `microbiologyevents.ab_itemid` | `…/CodeSystem/mimic-microbiology-antibiotic` |
| micro-test | `microbiologyevents.test_itemid` | `…/CodeSystem/mimic-microbiology-test` |
| vital-signs (ED) | *none* — hardcoded by column name | `http://loinc.org` |
| observation-ed | *none* — hardcoded by column name | `http://loinc.org` |

Two consequences a port must respect:

**`outputevents` and `datetimeevents` share one system** (`mimic-d-items`), so
`system` alone does not identify the stream. `system` + code still does, but only
because `d_items.itemid` is a global PK with one `linksto` per item — the three
ICU itemid sets are provably disjoint. If a future stream reuses an itemid, this
breaks silently. Do **not** fall back to `meta.profile`: the merged data
preparation collapses profile values across the Observation sub-profiles.

**The two ED streams carry no itemid at all** — the ETL hardcodes LOINC codes
keyed off the pivoted source column name. A concept touching ED vitals has no
itemid to filter on and must use those LOINC codes directly.

- Affected: every `Observation`-sourced concept port.
- Verified: 2026-08-07 — ETL SQL `fhir_observation_labevents.sql:13,111-113`
  and `:68-69` (dimension joined for `display` only);
  `fhir_observation_chartevents.sql:8,60-63`; `…_datetimeevents.sql:8,49-54`;
  `…_outputevents.sql:8,51-56`; `…_micro_org.sql:11,32,91-96`;
  `…_vitalsigns.sql:74-105`; `…_ed.sql:60-77`. Exact set **and** per-code count
  equality against the demo DuckDB oracle: labevents 498/498, chartevents
  1318/1318, datetimeevents 87/87, outputevents 39/39, micro_susc 25/25,
  micro_org 59/59, micro_test 71/71, zero mismatches. Pairwise itemid overlap
  between the three ICU tables is empty.

## The microbiology Observation streams aggregate rows

`micro_org` and `micro_test` group relational `microbiologyevents` rows before
emitting Observations — `micro_org` by `org_itemid × test_itemid ×
micro_specimen_id`, `micro_test` by specimen + test. FHIR row count is therefore
lower than relational row count even though every code value is verbatim. A
microbiology port must join on the grouping key, not assume one Observation per
source row. `micro_org` and `micro_susc` additionally drop rows where
`org_itemid` / `ab_itemid` is NULL.

- Affected: any concept reading `mimiciv_hosp.microbiologyevents`.
- Verified: 2026-08-07 — per-code counts match the oracle only when compared
  against `count(distinct micro_specimen_id)` per `test_itemid` (71/71 exact);
  raw row counts do not. `fhir_observation_micro_org.sql:11,32,91-96`,
  `…_micro_susc.sql:7,40,67-72`, `…_micro_test.sql:11,124-129`.

## HISTORICAL (fixed 2026-08-21) — labevents DST normalization changed dependent time-window aggregates

**FIXED UPSTREAM** by `ade10fb` (upstream #124) — see "READ FIRST" above. The
second-order mechanism recorded here (an anchor moves, and rows that were
outside a window fall inside it) is the general shape of what a shifted
timestamp does to a windowed concept, and worth keeping for that. It no longer
describes the served data.

- Affected: `Observation.effectiveDateTime` from labevents,
  `Specimen.collection.collectedDateTime`, and dependent concepts that window
  or aggregate blood-gas rows by `charttime`.
- Verified: `bg` attempt_0007 full-data comparison found 57 selected labevents
  rows across six specimens whose source 02:xx anchors were normalized to 03:xx
  by `mimic-fhir/sql/fhir_observation_labevents.sql:15,121`. Six unshifted 03:00
  FiO2 observations then entered bg's four-hour latest-preceding window after
  the anchor moved, accounting for all six residual second-order conflict rows;
  the direct and propagated set closed all 70 conflicts.
  `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58` preserves only the normalized
   collection time. The oracle wall times are not recoverable from served FHIR.

## ICU MedicationAdministration omits inputevent linkorderid

The ICU MedicationAdministration ETL does not serialize the source
`inputevents.linkorderid` as an identifier or other FHIR element. The source
administration row remains identifiable by its served resource only as opaque
identity; that identity cannot be inverted to recover the administrative
linkage value.

- Affected: `MedicationAdministration.identifier`,
  `MedicationAdministration.supportingInformation`, and source
  `inputevents.linkorderid`.
- Verified: full-data `phenylephrine` attempt_0003 found `linkorderid` non-NULL
  on all 193,260 oracle rows and candidate `NULL` on all 193,260 rows; the
  exhaustive ETL projection at `mimic-fhir/sql/fhir_medication_administration_icu.sql:7-23,38-100`
  writes no such element. The judge accepted it as ancillary administrative
  linkage.

## ICU MedicationAdministration Quantity values are served at decimal scale six

ICU MedicationAdministration dosage amount and rate Quantity values are
materialized in the served Delta warehouse at six-decimal precision. The
discarded low-order source precision is not retained in another FHIR element.

- Affected: `MedicationAdministration.dosage.dose.value` and
  `MedicationAdministration.dosage.rateQuantity.value`.
- Verified: full-data `phenylephrine` attempt_0003 traced the residual numeric
  differences to `mimic-fhir/sql/fhir_medication_administration_icu.sql:12,85-90`
  and `:14,91-99`; endpoint-aligned amount and rate values remained within the
  comparator tolerance, while the original low-order precision was not
  recoverable by any FHIR query.
- Attribution corrected 2026-08-26: the six-decimal cap is **Pathling's encoder**,
  not those ETL statements — see "Pathling encodes every FHIR decimal as
  `DECIMAL(32,6)`" below. The observed loss stands; only its cause was misplaced.
  This matters because no `mimic-fhir` patch can lift it.

## Pathling encodes every FHIR decimal as `DECIMAL(32,6)`

Not a MIMIC fact — a Pathling encoder fact, recorded here because it is what
actually caps served numeric precision across the whole warehouse. Any FHIR
`decimal` (`Quantity.value`, `Ratio` numerator/denominator, …) materializes as
`DECIMAL(32,6)`. Source values are **rounded to six decimal places at encode
time** and the discarded digits are gone; the cap is a fixed encoder constant,
so it cannot be lifted by changing `mimic-fhir` SQL or rebuilding the warehouse.

Two companion fields sit beside every decimal and neither recovers it:

- `<field>_scale INTEGER` — the *stored* scale, not the source scale. It is `6`
  on every row that has a value.
- `<field>._value_canonicalized STRUCT(value DECIMAL(38,0), scale INTEGER)` plus
  `_code_canonicalized` — the UCUM-canonical form, at much higher scale, but
  computed **from the already-truncated value** and populated only where the
  unit code parses as UCUM. The mimic-units codes mostly do not.

The practical consequence is threshold comparisons. `mimiciv_icu.inputevents.rate`
is `FLOAT` (float32, ~7 significant digits), so a source rate can sit a few
times 10⁻⁷ off a clinical cut-point purely as float32 representation noise, and
six-decimal rounding then lands it *on* the cut-point. Canonical SQL comparing
`> 0.1` or `> 5` flips branch. No cast, tolerance, or literal typing on the port
side recovers the side of the threshold — the discriminating digit is not served.

- Affected: every FHIR `decimal` in the Delta warehouse. Bites hardest on
  `MedicationAdministration.dosage.rateQuantity.value` for `mcg/kg/min`
  vasopressor rates, which never canonicalize.
- Verified: 2026-08-26 direct schema + data probe of the rebuilt demo warehouse
  `~/warehouses/mimic-iv-demo/delta/MedicationAdministration.parquet` —
  `rateQuantity` is `STRUCT(value DECIMAL(32,6), value_scale INTEGER, …,
  _value_canonicalized STRUCT(value DECIMAL(38,0), scale INTEGER),
  _code_canonicalized VARCHAR)`; `max(value_scale) = 6` on all 11,038 rate rows;
  `_value_canonicalized` is non-NULL on 93/93 `mg/min` rows and **0/2,585**
  `mcg/kg/min` rows. Consequence measured by full-data `first_day_sofa`
  attempt_0002: 24/73,181 stays diverge on `cardiovascular` and `sofa`, 20 with
  a norepinephrine max in `(0.1, 0.1000005]` served as `0.100000` and 4 with a
  dopamine max of `5.0000004768371582` — exactly 5.0 plus one float32 ULP —
  served as `5.000000`. Accepted by human override; the run is the worked example.
- Counts corrected 2026-08-26, later the same day: this entry first read 44,152
  rate rows, 0/10,340 `mcg/kg/min` and 372/372 `mg/min`. Those came from a
  `read_parquet('…/**/*.parquet')` glob, which reads **every Delta file version**
  rather than the current snapshot, and were uniformly 4× too high (226,140 rows /
  4 = 56,535 `MedicationAdministration` resources). An independent census of
  `MimicMedicationAdministrationICU.ndjson.zst` found 11,038 `rateQuantity`
  values, matching the corrected figure exactly. No conclusion changes; zero is
  still zero. **When probing this warehouse, read the Delta snapshot, not the
  file glob.** The inflated numbers survive verbatim in the immutable
  `state.json` justifications of `first_day_sofa` and `sofa`; both
  `human_override/` entries note it.
- The NDJSON reaches Pathling with the precision intact — it is not lost earlier.
  Census of the same demo file: 8,826 of 11,038 rate values (80.0%) carry more
  than six fractional digits in the raw JSON text, up to 18. One resource end to
  end: `72aff2c0-d201-54c9-b5d3-400774303963`, NDJSON
  `"value": 4.0460004806518555` (scale 16) → Delta `4.046000`, `value_scale` 6.
- The cap is `val scale: Int = 6` / `val precision: Int = 32` in the companion
  object of `au.csiro.pathling.encoders.datatypes.DecimalCustomCoder`
  (`DecimalCustomCoder.scala:131-133`) — a compile-time constant with no accessor,
  no `PathlingContext.create` option and no Spark conf. **Not a missed
  configuration in `step1_ndjson_to_delta.py`**; that script had no lever. The
  documented behaviour matches (`site/docs/libraries/io/schema.md:111-112`).
- **`_scale` is a documented `SHALL` the encoder does not honour.**
  `site/docs/libraries/io/schema.md:114-116` says the `_scale` field "SHALL be
  used to store the scale of the decimal value from the original FHIR data";
  `DecimalCustomCoder.scala:96-103` writes `min(6, source_scale)`. So the
  truncation is not merely lossy but *silent* — no served signal distinguishes a
  source that said `0.10000000894069672` from one that said `0.100000`. This is
  the one filable upstream defect in this class; the argued form, with a fix that
  preserves round-trip behaviour, is in `human_override/first_day_sofa.md:§5`.

## Current served Condition.code systems are proprietary MIMIC diagnosis systems

The current authoritative Delta warehouse serves hospital-linked diagnosis
codings under the proprietary MIMIC ICD systems, not the standard ICD URI
systems described by the older entry above. Ports must discriminate using the
served `system` plus the exact source code; no terminology translation is
needed.

- Affected: `Condition.code.coding.system` and ICD-9/ICD-10 diagnosis filters.
- Verified: `sapsii` attempt_0001 first probed the current Delta and matched
  4,506/4,506 hospital-linked diagnosis tuples, then the full-data comparison
  matched all 73,181/73,181 SAPS-II rows. The probe found 2,193 hospital ICD-9
  codings under `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd9`
  and 2,313 ICD-10 codings under
  `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-diagnosis-icd10`.
