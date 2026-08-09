# MIMIC_NOTES.md — cross-concept knowledge about the MIMIC-on-FHIR data

Dataset/IG-level quirks that hold regardless of which concept is being ported.
Read this **before** probing the IG or authoring a ViewDefinition or SQL. When you discover a new quirk, check for an existing
entry and update it rather than duplicating; concept-specific findings belong
in that attempt's `evidence/<stage>.md` instead.

Entry format: short claim · affected resource/field · one line on how it was
verified (so a future agent can trust-but-recheck cheaply).

**This file is mutable and shared — it is the one document outside the
write-once attempt regime.** Attempt artifacts are immutable; this is not. Edit
it in place: update an existing entry when you sharpen or contradict it, append
a new `##` section when the quirk is genuinely new. Never rewrite an entry to
erase what it used to say without saying why in the verified line.

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

---

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

## `Patient.birthDate` is NOT `anchor_year - anchor_age` — it is `MIN(transfers.intime) - anchor_age`

**The demo-validated assumption that `birthDate.year == anchor_year - anchor_age`
does NOT hold on full data.** The upstream ETL synthesises `birthDate` from the
patient's earliest transfer time, not from the anchor pair:
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

The UUID keys are still needed, as the **join** keys between resources
(`Observation.subject.getReferenceKey(Patient)` = `Patient.getResourceKey()`).
Project both: the UUID to join on, the identifier value to emit.

- Affected: `Patient.identifier`, `Encounter.identifier`; every concept whose
  output carries `subject_id`, `hadm_id` or `stay_id` — i.e. nearly all of them.
- Verified: 2026-08-07, `demographics/age` attempt_0001 — SQL executed, 275 rows,
  all 6 column names matched, `shape_fail` on exactly two columns:
  `subject_id` VARCHAR (from `getResourceKey()`) and `hadm_id` VARCHAR (from
  `identifier.value`, uncast) against `INTEGER` in the manifest. See that
  attempt's `shape.demo.json` and `carryover/age/fhir-prober.md`, which had both
  systems and the VARCHAR typing right before the SQL was written.

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

**DST-gap timestamps are irreversibly shifted +1 hour.** The upstream ETL
casts naive MIMIC `admittime` through `TIMESTAMPTZ` (`mimic-fhir/sql/fhir_encounter.sql:65`),
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

- Affected: categorical `mimic-observation-chartevents` items.
- Verified: lin-2025 `tmp/probe_data2.py` (226732 value_cc empty; value_str populated).

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
