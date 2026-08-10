# Source analysis — `medication/antibiotic`

Canonical SQL: `mimic-iv/concepts/medication/antibiotic.sql` (203 lines)
DAG node: stem `antibiotic`, path `medication/antibiotic.sql`, level 0,
`dependencies: []`, `dependents: ["suspicion_of_infection"]`.

This concept is a **medication-name pattern classifier**, not a code-filtered
stream. It flags a row as an antibiotic by substring (LIKE) matching against the
free-text `prescriptions.drug` name and by excluding certain routes / dosage
forms. There is **no itemid filter and no ICD filter**. The "code set" is a set
of literal drug-name substrings plus an excluded `drug_type` literal and a set
of excluded route codes. Note for the port: `drug` is free text; on the FHIR
side it survives as `Medication.identifier` with the
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name` system (see
`MIMIC_NOTES.md` — "Prescription Medication.code prefers NDC/formulary..."),
NOT as `Medication.code.coding.code`. Route is `MedicationRequest`/prescription
route.

---

## 1. Table references

| Alias | Schema | Table | Used in |
|---|---|---|---|
| — (unnamed) | `mimiciv_hosp` | `prescriptions` | CTE `abx` FROM |
| `pr` | `mimiciv_hosp` | `prescriptions` | main SELECT FROM |
| `ie` | `mimiciv_icu` | `icustays` | main SELECT LEFT JOIN |

Both are **raw** tables; there is **no `mimiciv_derived` dependency** (DAG
confirms `dependencies: []`).

## 2. Columns

CTE `abx` (output): `drug` (string), `route` (string), `antibiotic` (integer,
CASE result `1`/`0`).

Main SELECT output columns:
- `subject_id` — INTEGER (from `pr.subject_id`)
- `hadm_id` — INTEGER (from `pr.hadm_id`)
- `stay_id` — INTEGER (from `ie.stay_id`; NULL when no matching ICU stay)
- `antibiotic` — string (this is `pr.drug` renamed, **not** the CTE flag; the
  output column is the drug name)
- `route` — string (from `pr.route`)
- `starttime` — TIMESTAMP (from `pr.starttime`)
- `stoptime` — TIMESTAMP (from `pr.stoptime`)

Referenced in joins/filters: `pr.drug`, `pr.route`, `pr.hadm_id`,
`pr.drug_type`, `ie.hadm_id`, `ie.intime`, `ie.outtime`.

## 3. Filters

CTE `abx` (all `WHERE` predicates on `mimiciv_hosp.prescriptions`):
- `drug_type NOT IN ('BASE')`
- `route NOT IN ('OU','OS','OD','AU','AS','AD','TP')`
- `LOWER(route) NOT LIKE '%ear%'`
- `LOWER(route) NOT LIKE '%eye%'`
- `LOWER(drug) NOT LIKE '%cream%'`
- `LOWER(drug) NOT LIKE '%desensitization%'`
- `LOWER(drug) NOT LIKE '%ophth oint%'`
- `LOWER(drug) NOT LIKE '%gel%'`

Main SELECT:
- `abx.antibiotic = 1` (keeps only rows the CASE flag classified as antibiotic)

The CASE in CTE `abx` assigns `antibiotic = 1` when `LOWER(drug)` LIKE-matches
any of the listed fragments (else `0`). `SELECT DISTINCT` collapses `(drug,
route)` pairs.

## 4. Joins

- `INNER JOIN abx ON pr.drug = abx.drug AND pr.route = abx.route`
- `LEFT JOIN mimiciv_icu.icustays ie ON pr.hadm_id = ie.hadm_id AND pr.starttime >= ie.intime AND pr.starttime < ie.outtime`

The `icustays` join is a **temporal** join: an ICU stay whose `[intime, outtime)`
interval contains the prescription `starttime`. A prescription may match 0..N
stays; the LEFT JOIN with them can therefore fan out a `pr` row across stays
(same `starttime` falling inside multiple `icustays`), which is why `stay_id`
can repeat — this is the sepsis-3 oriented use of the table.

## 5. `mimiciv_derived` dependencies

**None.** Raw tables only.

## 6. Aggregations

- `SELECT DISTINCT` in CTE `abx` (dedup of `(drug, route)`).
- No `GROUP BY`, no window functions, no `MIN`/`MAX`/`AVG`/`ARRAY_AGG`.

## 7. Literal code set (verbatim)

There is no `itemid` and no ICD code. Two kinds of literal predicate values feed
different output columns:

### Excluded route codes (feed the `route` filtering; exclude rows)
Source table: `mimiciv_hosp.prescriptions`, column `route`.
Values (string): `OU`, `OS`, `OD`, `AU`, `AS`, `AD`, `TP`.

### Excluded `drug_type` (feed the `drug_type` filtering; exclude rows)
Source table: `mimiciv_hosp.prescriptions`, column `drug_type`.
Value (string): `BASE`.

### Route/drug substrings (LIKE exclusions)
Source table: `mimiciv_hosp.prescriptions`, columns `route` and `drug`.
- on `route` (LOWER): `%ear%`, `%eye%`
- on `drug` (LOWER): `%cream%`, `%desensitization%`, `%ophth oint%`, `%gel%`

### Antibiotic drug-name fragments (feed the CASE → `abx.antibiotic` flag)
Source table: `mimiciv_hosp.prescriptions`, column `drug` (matched on
`LOWER(drug)`). Each is a `LIKE '%<fragment>%'`; any match sets `antibiotic=1`.
Recorded verbatim, in source order (duplicates retained as-is per coding
policy — `septra` appears at lines 131 and 133, `trimethoprim` at 139 and 148):

```
adoxa, ala-tet, alodox, amikacin, amikin, amoxicill, amphotericin,
anidulafungin, ancef, clavulanate, ampicillin, augmentin, avelox, avidoxy,
azactam, azithromycin, aztreonam, axetil, bactocill, bactrim, bactroban,
bethkis, biaxin, bicillin l-a, cayston, cefazolin, cedax, cefoxitin,
ceftazidime, cefaclor, cefadroxil, cefdinir, cefditoren, cefepime, cefotan,
cefotetan, cefotaxime, ceftaroline, cefpodoxime, cefpirome, cefprozil,
ceftibuten, ceftin, ceftriaxone, cefuroxime, cephalexin, cephalothin,
cephapririn, chloramphenicol, cipro, ciprofloxacin, claforan,
clarithromycin, cleocin, clindamycin, cubicin, dicloxacillin, dirithromycin,
doryx, doxycy, duricef, dynacin, ery-tab, eryped, eryc, erythrocin,
erythromycin, factive, flagyl, fortaz, furadantin, garamycin, gentamicin,
kanamycin, keflex, kefzol, ketek, levaquin, levofloxacin, lincocin, linezolid,
macrobid, macrodantin, maxipime, mefoxin, metronidazole, meropenem,
methicillin, minocin, minocycline, monodox, monurol, morgidox, moxatag,
moxifloxacin, mupirocin, myrac, nafcillin, neomycin, nicazel doxy 30,
nitrofurantoin, norfloxacin, noroxin, ocudox, ofloxacin, omnicef, oracea,
oraxyl, oxacillin, pc pen vk, pce dispertab, panixine, pediazole, penicillin,
periostat, pfizerpen, piperacillin, tazobactam, primsol, proquin, raniclor,
rifadin, rifampin, rocephin, smz-tmp, septra, septra ds, septra, solodyn,
spectracef, streptomycin, sulfadiazine, sulfamethoxazole, trimethoprim,
sulfatrim, sulfisoxazole, suprax, synercid, tazicef, tetracycline, timentin,
tobramycin, trimethoprim, unasyn, vancocin, vancomycin, vantin, vibativ,
vibra-tabs, vibramycin, zinacef, zithromax, zosyn, zyvox
```

### Dead-filter note
No itemid filters exist in this concept, so there is no `bg`-style dead itemid
to record as expected-absent. The code set is entirely free-text/route based.

---

## Notes for downstream agents

- The output column named `antibiotic` is `pr.drug` (the matched drug NAME), not
  the boolean flag; the flag exists only inside CTE `abx` as the filter gate.
- The coding system on the FHIR side for `drug` is the `mimic-medication-name`
  identifier, not a `Medication.code.coding.code` — see `MIMIC_NOTES.md`
  "Prescription Medication.code prefers NDC/formulary...".
- `subject_id`, `hadm_id` come from `Patient`/`Encounter` identifiers as
  STRINGs and must be `CAST(... AS INTEGER)` — see `MIMIC_NOTES.md` "MIMIC ids
  live in `identifier.value` as STRINGs".
- `starttime`/`stoptime` come from `MedicationRequest.dispenseRequest.validityPeriod`
  start/end, expressed in `[intime, outtime)` window matching via the ICU
  `Encounter`; validity intervals that are missing or invalid (`start > stop`)
  are not recoverable from the served request — see `MIMIC_NOTES.md`
  "MedicationRequest omits invalid or incomplete prescription validity periods".
  This is a likely source of `only_oracle` / `differing_null_only` divergence.
- Datetimes must be cast with `CAST(... AS TIMESTAMP_NTZ)` per `MIMIC_NOTES.md`.
