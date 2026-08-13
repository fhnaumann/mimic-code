# Source analysis: `norepinephrine`

## Source and DAG identity

- Canonical SQL: `mimic-iv/concepts/medication/norepinephrine.sql`.
- The DAG node is `norepinephrine`, path `medication/norepinephrine.sql`,
  build level 0, with SHA256
  `4972b33d3dce3aa0f8626f790b19d4cff033436e0910845f795c7e2a55ec1d28`.
- The checked file hashes to that exact SHA256. The DAG lists no
  `mimiciv_derived` dependencies. Its DAG dependents are `first_day_sofa`,
  `sofa`, and `vasoactive_agent`; those are consumers, not inputs to this
  concept.
- The source uses BigQuery-style backtick qualification and the
  `physionet-data` project prefix, but the DAG-resolved logical source table
  is `mimiciv_icu.inputevents`.

## Tables and joins

There is one table reference and no joins:

| SQL clause | Logical schema | Table | Alias | Join condition/type |
|---|---|---|---|---|
| `FROM` | `mimiciv_icu` | `inputevents` | none | not applicable |

There are no references to `mimiciv_hosp` and no references to any table in
`mimiciv_derived`.

## Output columns and inferred types

The query has no CTE or intermediate relation. It emits one projected row for
each qualifying `inputevents` source row, with this output shape:

| Output column | Expression | Inferred source/output type | Meaning in the SQL |
|---|---|---|---|
| `stay_id` | `stay_id` | `INT64`/integer, nullable in the source schema | ICU stay identifier |
| `linkorderid` | `linkorderid` | `INT64`/integer, nullable | Input-event linked-order identifier |
| `vaso_rate` | the `CASE` over `rateuom`, `patientweight`, and `rate` | `FLOAT64`/floating-point | Rate normalized by the query's unit rules, intended by the comments to be mcg/kg/min (also equivalent to ug/kg/min) |
| `vaso_amount` | `amount` | `FLOAT64`/floating-point, nullable | Raw input-event amount; no amount conversion is performed |
| `starttime` | `starttime` | `DATETIME` | Administration interval start |
| `endtime` | `endtime` | `DATETIME` | Administration interval end |

The source fields referenced anywhere in the final query are:

- `stay_id` (`INT64`, nullable in the published inputevents schema): output
  ICU-stay identity.
- `linkorderid` (`INT64`, nullable): output linked-order value.
- `rateuom` (`STRING`): controls both numeric conversion branches for
  `vaso_rate`.
- `patientweight` (`FLOAT64`, nullable): special discriminator in the first
  conversion branch.
- `rate` (`FLOAT64`, nullable): source rate and input to the normalized rate.
- `amount` (`FLOAT64`, nullable): copied to `vaso_amount`.
- `starttime` and `endtime` (`DATETIME`, required in the inputevents schema):
  copied unchanged by the canonical SQL to the output columns.
- `itemid` (`INT64`, required): row-inclusion discriminator; it is not
  projected.

Fields present in `inputevents` but not referenced by this SQL (including
`subject_id`, `hadm_id`, `orderid`, `amountuom`, and `storetime`) do not affect
this query's result directly.

## Filters and value transformation

The only `WHERE` predicate is:

```sql
WHERE itemid = 221906 -- norepinephrine
```

There is no time window, `stay_id` restriction, null check, amount/rate
constraint, unit exclusion, or additional code exclusion. Rows with null
`rate`, null `amount`, null `patientweight`, or other unit strings are not
removed by the query.

`vaso_rate` is calculated as follows, in SQL three-valued-logic order:

```sql
CASE
    WHEN rateuom = 'mg/kg/min' AND patientweight = 1 THEN rate
    WHEN rateuom = 'mg/kg/min' THEN rate * 1000.0
    ELSE rate
END AS vaso_rate
```

Thus, an exact `rateuom` of `mg/kg/min` normally multiplies the rate by
`1000.0`, except when `patientweight` is exactly numeric `1`, where the raw
rate is retained. If `patientweight` is null, the first predicate is not true
and the second branch still applies when `rateuom` is exactly
`'mg/kg/min'`. Every other unit value, including null, takes the raw-rate
`ELSE` branch. `vaso_amount` is a direct copy of `amount`; the SQL does not
use `amountuom` or convert amount units.

## Literal code specification

The complete coded filter set in the canonical SQL is:

| Source table filtered | Source field | Exact literal as written | Feeds |
|---|---|---|---|
| `mimiciv_icu.inputevents` | `itemid` | `221906` | Inclusion of rows in the final result; all output columns, especially the norepinephrine administration stream |

No ICD code, coding-system literal, or second itemid is named by this SQL.
The unit/discriminator literals are not code sets, but are also preserved
verbatim here because they alter the clinically meaningful derived value:
`'mg/kg/min'`, `1`, and `1000.0`.

In the MIMIC-on-FHIR context read for this analysis, the ICU
`MedicationAdministration.medication` code is served under
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu`, with the
itemid carried as the exact string code `221906`. That FHIR system is ETL
context, not an additional source-SQL filter or a translated code set.

## Aggregations, windows, and grain/key implications

- There is no `GROUP BY`, aggregate, `DISTINCT`, window function, or value
  aggregation.
- The natural grain is the filtered raw `mimiciv_icu.inputevents` row: one
  output row per source input-event row whose `itemid` is `221906`.
- The repository's ICU DDL declares the raw `inputevents` primary key as
  `(orderid, itemid)`. Since this concept fixes `itemid` to `221906`, source
  `orderid` is the implied unique row key under that schema constraint, but
  `orderid` is not projected by the canonical concept. The projected tuple
  `(stay_id, linkorderid, starttime, endtime, vaso_rate, vaso_amount)` must not
  be assumed unique: `linkorderid` is nullable and can be shared across rows,
  and the query omits the source `orderid` and other source identity fields.
- `stay_id` scopes the event to an ICU stay. `starttime`/`endtime` preserve the
  administration interval and are the temporal identity available in the
  output. `linkorderid` is the only order-linkage field exposed by this
  concept, so its absence or nulling can affect a downstream natural-key or
  linkage comparison even though it does not participate in the `WHERE` or
  `CASE` expressions.
- The row identity is the source inputevent row, not a distinct medication
  name or a stay-level summary. There is no carry-forward or interval
  splitting in this concept; interval reconstruction appears only in the
  separate `vasoactive_agent` dependent concept.

## Semantically essential inputs

These are the source fields/discriminators whose values control inclusion,
identity, timing, or a clinically meaningful output:

1. **`itemid`** — the exact `221906` filter controls whether the row exists at
   all. It also identifies the norepinephrine stream, although it is omitted
   from the output columns.
2. **`stay_id`** — carries ICU-stay identity into every output row and is the
   principal encounter scope. It is part of the source event's natural
   identity and is used by all downstream vasoactive interval logic.
3. **`linkorderid`** — is explicitly output and carries source order linkage.
   It does not change row inclusion or the rate formula, but it can distinguish
   or link source administrations and therefore is key-sensitive rather than
   an incidental unused field.
4. **`starttime` and `endtime`** — are copied into the result and define the
   administration interval. They control temporal interpretation by downstream
   concepts even though this SQL does not compare them in a filter.
5. **`rate`** — supplies the raw rate, becomes `vaso_rate` in the normal/ELSE
   path, and is the numeric input after conversion in the mg/kg/min path. A
   null rate is retained and yields a null `vaso_rate` unless a numeric source
   value is present.
6. **`rateuom`** — selects the mg/kg/min conversion path versus the raw-rate
   path. Exact spelling and whitespace matter to this SQL because it compares
   the untrimmed source value to the exact literal `'mg/kg/min'`.
7. **`patientweight`** — only the exact value `1` changes the mg/kg/min
   conversion, causing the raw rate to be retained instead of multiplied by
   `1000.0`. It is therefore an input to the derived clinical value even
   though it is not output.
8. **`amount`** — is copied to `vaso_amount` and can be null; it does not
   affect row inclusion or the rate calculation.

`amountuom` is not semantically essential to this SQL's output because the
query intentionally does not select or inspect it. Likewise, `orderid` may
be part of raw input-event/resource identity upstream, but it is not selected,
filtered, or used in a calculation by this canonical concept.

## Likely MIMIC-on-FHIR representability issues

These are mapping risks to verify against served FHIR data; they are not a
terminal equivalence decision.

1. **`linkorderid` is not carried by ICU MedicationAdministration.** The
   contextual ICU ETL creates one `MedicationAdministration` per inputevent
   and writes medication code, dosage, effective timing, subject, and ICU
   encounter, but no `linkorderid` or inputevent identifier. A resource UUID
   built from `stay_id`/`orderid`/`itemid` is opaque identity and must not be
   parsed or inverted to recover `linkorderid`. Since this concept exposes
   `linkorderid`, the loss may be key/linkage-essential rather than merely an
   ancillary null; the prober must check multiplicity and the comparator key.
2. **`patientweight` is not present in the MedicationAdministration dosage.**
   The FHIR dosage carries the raw rate and unit, but the source-only
   `patientweight = 1` exception is needed to reproduce `vaso_rate` exactly
   for the affected mg/kg/min rows. No weight join is part of the canonical
   query, so substituting a separately observed weight would not be the same
   source operation without evidence.
3. **The raw unit is normalized by the FHIR ETL, while this SQL compares the
   source string exactly.** The source uses untrimmed `rateuom`; the ICU FHIR
   ETL trims it before writing `rateQuantity.unit/code`. If any matching row
   contains surrounding whitespace, the source can take the raw-rate `ELSE`
   path while FHIR exposes the trimmed unit, losing the discriminator needed
   to replay that branch.
4. **`effective[x]` is conditional on rate presence.** The ICU ETL writes an
   `effectivePeriod` from source start/end when raw `rate` is non-null, but
   writes only an `effectiveDateTime` from source `endtime` when raw `rate` is
   null. This concept retains both times for all filtered rows, so a null-rate
   row can lose `starttime`; both FHIR choice variants must be considered.
5. **FHIR datetime ETL can normalize DST-gap wall times.** Source MIMIC
   `DATETIME` values are de-identified wall-clock values, whereas the upstream
   ICU MedicationAdministration ETL casts endpoints through `TIMESTAMPTZ`.
   A nonexistent New York spring-forward time can therefore appear one hour
   later in FHIR. The original wall time is not recoverable from the served
   effective value, so exact `starttime`/`endtime` comparison may have a small
   intrinsic conflict set.
6. **Numeric precision can differ.** The served ICU MedicationAdministration
   Quantity values are represented at decimal scale six in the contextual
   probes/fragments. The source rates and amounts are `FLOAT64`, and the
   `rate * 1000.0` branch can therefore show small representation differences
   even where the value is otherwise preserved.
7. **The itemid filter itself is comparatively representable.** The contextual
   ETL writes the inputevent itemid verbatim as the medication coding code
   under the ICU medication code system, so `221906` should be filtered as an
   exact string code, without terminology translation. This does not solve
   the missing linkage, unit discriminator, timing, or precision issues above.

## Context checked and authority boundaries

I read `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, including the coding policy
context for itemid-derived observations, opaque resource identifiers,
polymorphic effective fields, datetime handling, and essential-source-loss
policy. I also checked the provisional fragments
`MIMIC_NOTES.d/epinephrine.md`, `MIMIC_NOTES.d/dobutamine.md`, and
`MIMIC_NOTES.d/dopamine.md` because they concern the same ICU
MedicationAdministration ETL. Those fragments were treated as leads/context,
not as authoritative findings for norepinephrine. The ETL source inspected for
the representability discussion was
`/Users/nau025/Documents/mimic-fhir/sql/fhir_medication_administration_icu.sql`.
The source inputevents type reference inspected was
`mimic-iv/buildmimic/bigquery/schemas/icu/inputevents.json`.
