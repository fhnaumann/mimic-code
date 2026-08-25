# Source analysis: `ventilation`

## Scope and DAG identity

- Concept stem: `ventilation`.
- DAG-resolved canonical SQL: `mimic-iv/concepts/treatment/ventilation.sql`.
- DAG node: level `1`; SHA256
  `8d7ce56f2d71c8aab18625c7af03c7324cdabfd87c8a431077d755672909a2b2`.
- DAG dependencies, in the stored order: `oxygen_delivery`,
  `ventilator_setting`.
- DAG dependents: `apsiii`, `first_day_sofa`, `lods`, `oasis`, `sapsii`,
  `sofa`.
- `uv run mimic_utils concept_dag --check` passed: the stored DAG and generated
  DAG agree. No SQL was executed for this analysis.

The dependency views are available to candidate SQL under their unqualified
stems. The ventilation port must consume `FROM oxygen_delivery` and
`FROM ventilator_setting`; it must not rederive either dependency from FHIR or
inline its raw-table logic.

## Table and relation references

The ventilation SQL itself has no direct `mimiciv_hosp` or `mimiciv_icu` table
reference. Every physical relation it names is in `mimiciv_derived`:

| SQL location | Type | Schema/table or CTE | Columns consumed by ventilation |
|---|---|---|---|
| `tm`, line 26 | `FROM` | `mimiciv_derived.ventilator_setting` (dependency stem `ventilator_setting`) | `stay_id`, `charttime` |
| `tm`, line 29 | `FROM` | `mimiciv_derived.oxygen_delivery` (dependency stem `oxygen_delivery`) | `stay_id`, `charttime` |
| `vs`, line 156 | `FROM` | local CTE `tm` | `stay_id`, `charttime` |
| `vs`, lines 157–159 | `LEFT JOIN` | `mimiciv_derived.ventilator_setting` AS `vs` | `stay_id`, `charttime`, `ventilator_mode`, `ventilator_mode_hamilton` |
| `vs`, lines 160–162 | `LEFT JOIN` | `mimiciv_derived.oxygen_delivery` AS `od` | `stay_id`, `charttime`, `o2_delivery_device_1` through `_4` |

The source SQL uses the dataset-qualified spelling
``physionet-data.mimiciv_derived.<stem>``. In the port's preprocessed
candidate environment, the corresponding table names are the unqualified
dependency stems above. The dependency SQLs independently read
`mimiciv_icu.chartevents`; that is not a direct table reference of this
concept and must remain encapsulated in those dependency concepts.

## Dependency interface and types

These are the exact dependency columns the consumer reads:

| Dependency | Exact consumer columns | Inferred type | Consumer use |
|---|---|---|---|
| `oxygen_delivery` | `stay_id` | `INTEGER` | Event-grid key and both LEFT JOIN keys; carried to all output episodes |
| `oxygen_delivery` | `charttime` | `DATETIME`/`TIMESTAMP` | Event-grid key, both LEFT JOIN keys, chronological ordering and interval boundaries |
| `oxygen_delivery` | `o2_delivery_device_1` | `VARCHAR`/`STRING` | Tracheostomy, endotracheal-tube, NIV, HFNC, supplemental-oxygen and None branches |
| `oxygen_delivery` | `o2_delivery_device_2` | `VARCHAR`/`STRING` | NIV branch only |
| `oxygen_delivery` | `o2_delivery_device_3` | `VARCHAR`/`STRING` | NIV branch only |
| `oxygen_delivery` | `o2_delivery_device_4` | `VARCHAR`/`STRING` | NIV branch only |
| `ventilator_setting` | `stay_id` | `INTEGER` | Event-grid key and both LEFT JOIN keys |
| `ventilator_setting` | `charttime` | `DATETIME`/`TIMESTAMP` | Event-grid key, both LEFT JOIN keys, chronological ordering and interval boundaries |
| `ventilator_setting` | `ventilator_mode` | `VARCHAR`/`STRING` | Invasive-ventilator mode branch |
| `ventilator_setting` | `ventilator_mode_hamilton` | `VARCHAR`/`STRING` | Hamilton invasive-mode and Hamilton NIV branches |

The dependency outputs also contain other columns, including `subject_id`, but
ventilation does not read them. It does not read oxygen flows, ventilator
numeric settings, `ventilator_type`, units, or dependency row identifiers.
Both dependency SQLs group their raw ICU rows by `(subject_id, charttime)` and
emit `MAX(stay_id)`; ventilation deliberately joins the resulting contracts by
`(stay_id, charttime)`, not by `subject_id`.

## CTE schemas and column flow

Types below follow the canonical BigQuery convention where applicable (`INT64`,
`DATETIME`, `FLOAT64`, and `STRING`), with the equivalent checked-in MIMIC
PostgreSQL names shown as `INTEGER`, `TIMESTAMP`, `FLOAT`, and `VARCHAR`.
Nullable means the SQL can produce NULL at that stage; it does not assert FHIR
representability.

### `tm` (lines 24–30)

`tm` selects only:

| Column | Type | Expression/use |
|---|---|---|
| `stay_id` | `INTEGER` | Direct from either dependency; event-grid key |
| `charttime` | `DATETIME`/`TIMESTAMP` | Direct from either dependency; event-grid key |

The two selects are combined with `UNION DISTINCT`, so the intended `tm` grain
is one row per distinct `(stay_id, charttime)` found in either dependency.
There is no `subject_id` in this CTE.

### `vs` (lines 32–163)

The `vs` CTE starts at `tm` grain and LEFT JOINs both dependencies on the exact
stay/time pair. Its selected columns are:

| Column | Type | Expression/provenance and use |
|---|---|---|
| `stay_id` | `INTEGER` | `tm.stay_id`; carried forward |
| `charttime` | `DATETIME`/`TIMESTAMP` | `tm.charttime`; carried forward |
| `o2_delivery_device_1` | nullable `STRING` | `od`; classification input |
| `vent_mode` | nullable `STRING` | `COALESCE(ventilator_mode, ventilator_mode_hamilton)`; selected for debug only and never referenced later |
| `ventilation_status` | nullable `STRING` | CASE result; one of the six category strings or NULL |

Although the alias `vent_mode` is computed, the classification CASE does **not**
use it. It separately references raw `ventilator_mode` and
`ventilator_mode_hamilton` from the ventilator-setting join. The device CASE
also references `o2_delivery_device_2`, `_3`, and `_4`; those columns are
referenced but not selected as standalone `vs` output columns. Thus the full
set of source columns used by the CASE is `o2_delivery_device_1`–`_4`,
`ventilator_mode`, and `ventilator_mode_hamilton`.

### `vd0` (lines 165–185)

`vd0` removes NULL classifications before its window functions:

| Column | Type | Expression/use |
|---|---|---|
| `stay_id` | `INTEGER` | Direct from `vs`; partition/output scope |
| `charttime` | temporal | Direct from `vs`; ordering and output |
| `charttime_lag` | temporal, nullable | `LAG(charttime, 1)` within `(stay_id, ventilation_status)` ordered by `charttime` |
| `charttime_lead` | temporal, nullable | `LEAD(charttime, 1)` within `w`, the `(stay_id)` chronological stream |
| `ventilation_status` | `STRING` | Non-NULL CASE result |
| `ventilation_status_lag` | nullable `STRING` | `LAG(ventilation_status, 1)` within `w` |

The named window is exactly:

```sql
WINDOW w AS (PARTITION BY stay_id ORDER BY charttime)
```

`charttime_lead` therefore looks at the next non-NULL-status row regardless of
whether its category changes. `charttime_lag` is instead partitioned by both
stay and status, so the 14-hour test below compares with the previous
same-status timestamp, not necessarily the immediately preceding row.

### `vd1` (lines 187–214)

`vd1` selects:

| Column | Type | Expression/use |
|---|---|---|
| `stay_id` | `INTEGER` | Passed through |
| `charttime` | temporal | Passed through |
| `charttime_lag` | temporal, nullable | Passed through from `vd0` |
| `charttime_lead` | temporal, nullable | Passed through from `vd0` |
| `ventilation_status` | `STRING` | Passed through |
| `ventduration` | `FLOAT`/`DOUBLE` | `DATETIME_DIFF(charttime, charttime_lag, MINUTE) / 60`; carried later but not used in the final SELECT |
| `new_ventilation_event` | integer (`INT64`/`INTEGER`) | CASE flag, `1` for a new event and `0` for continuation |

The event flag is `1` when `ventilation_status_lag IS NULL`, when
`DATETIME_DIFF(charttime, charttime_lag, HOUR) >= 14`, or when
`ventilation_status_lag != ventilation_status`; otherwise it is `0`.

### `vd2` (lines 216–229)

`vd2` selects:

| Column | Type | Expression/use |
|---|---|---|
| `stay_id` | `INTEGER` | Partition/output scope |
| `charttime` | temporal | Cumulative ordering and final start/end aggregate |
| `charttime_lead` | temporal, nullable | Final endtime candidate |
| `ventilation_status` | `STRING` | Final status aggregate |
| `ventduration` | `FLOAT`/`DOUBLE` | Carried but unused in final output |
| `new_ventilation_event` | integer | Input to cumulative sum |
| `vent_seq` | integer (`INT64`/`BIGINT`) | `SUM(new_ventilation_event) OVER (PARTITION BY stay_id ORDER BY charttime)`; internal episode number |

The cumulative window has no explicit frame clause; its ordinary ordered
running-sum semantics are intended.

### Final output (lines 231–255)

| Output column | SQL expression | Inferred type | Meaning |
|---|---|---|---|
| `stay_id` | `stay_id` | `INTEGER` | ICU stay identifier and output episode scope |
| `starttime` | `MIN(charttime)` | temporal `DATETIME`/`TIMESTAMP` | First documented non-NULL-status time in the episode |
| `endtime` | `MAX(CASE ... END)` | temporal `DATETIME`/`TIMESTAMP` | Next documented status time, except at a terminal row or a >=14-hour next gap, where the current `charttime` is used |
| `ventilation_status` | `MAX(ventilation_status)` | `STRING` | Episode category; all rows in a `vent_seq` are intended to share it |

The final query groups by `stay_id, vent_seq` and does not expose `vent_seq`.
The visible semantic grain is one classified ventilation interval per ICU stay
and internal episode sequence. In a normal dependency result this is naturally
identified by `(stay_id, starttime)`, but the SQL's actual grouping key is
`(stay_id, vent_seq)` and the sequence must not be replaced by a guessed source
identifier.

## Filters and predicates

The only executable `WHERE` predicate in the ventilation SQL is:

```sql
WHERE ventilation_status IS NOT NULL
```

It is in `vd0`, before all windows. Rows whose classification CASE falls to
NULL are removed; the windows and all final aggregates see only classified
rows. There are no raw itemid filters, ICD filters, code exclusions, value
range constraints, admission filters, or explicit time-window WHERE clauses in
this concept.

The final query has this executable group filter:

```sql
HAVING MIN(charttime) != MAX(charttime)
```

Therefore a sequence with only one distinct charttime is not emitted. The
14-hour temporal predicates are CASE conditions, not WHERE filters:

```sql
DATETIME_DIFF(charttime, charttime_lag, HOUR) >= 14
DATETIME_DIFF(charttime_lead, charttime, HOUR) >= 14
```

The second determines whether an episode ends at the current row or at the
next documented row. The first determines whether a new episode sequence is
started. The status inequality is also an inclusion/segmentation discriminator:
`ventilation_status_lag != ventilation_status` starts a new sequence.

## Joins and their exact conditions

All joins in `vs` are `LEFT JOIN`s; there are no INNER joins:

```sql
LEFT JOIN `physionet-data.mimiciv_derived.ventilator_setting` vs
    ON tm.stay_id = vs.stay_id
   AND tm.charttime = vs.charttime

LEFT JOIN `physionet-data.mimiciv_derived.oxygen_delivery` od
    ON tm.stay_id = od.stay_id
   AND tm.charttime = od.charttime
```

There is no `subject_id` predicate in either join. The CTE reference
`FROM tm` is not a physical-table join; `tm` is the unioned event grid.

## Literal code specification — exact SQL values

Ventilation has no numeric `itemid` or ICD code filter of its own. Its coded
filters are exact string values from the two dependency outputs. The source
table for every device set below is `mimiciv_derived.oxygen_delivery` (alias
`od`), and the source table for every ventilator-mode set is
`mimiciv_derived.ventilator_setting` (alias `vs`). Every matching literal feeds
the `ventilation_status` CASE in CTE `vs`, then the final
`ventilation_status` output. Trailing spaces inside the quoted SQL literals
are significant and are retained below.

### Oxygen-device sets (`oxygen_delivery`)

```sql
o2_delivery_device_1 IN
(
    'Tracheostomy tube'
    , 'Trach mask '
)
```

Feeds status literal `'Tracheostomy'`.

```sql
o2_delivery_device_1 IN
(
    'Endotracheal tube'
)
```

Feeds the invasive-ventilation branch, whose status literal is
`'InvasiveVent'`.

The four NIV device-slot filters are separate predicates in the source SQL:

```sql
o2_delivery_device_1 IN
(
    'Bipap mask '
    , 'CPAP mask '
)

o2_delivery_device_2 IN ('Bipap mask ', 'CPAP mask ')

o2_delivery_device_3 IN ('Bipap mask ', 'CPAP mask ')

o2_delivery_device_4 IN ('Bipap mask ', 'CPAP mask ')
```

Each feeds the `'NonInvasiveVent'` status branch. The values are repeated in
the source predicate for each slot; they are not a single normalized set.

The remaining device filters are:

```sql
o2_delivery_device_1 IN
(
    'High flow nasal cannula'
)
```

Feeds `'HFNC'`.

```sql
o2_delivery_device_1 IN
(
    'Non-rebreather'
    , 'Face tent'
    , 'Aerosol-cool'
    , 'Venti mask '
    , 'Medium conc mask '
    , 'Ultrasonic neb'
    , 'Vapomist'
    , 'Oxymizer'
    , 'High flow neb'
    , 'Nasal cannula'
)
```

Feeds `'SupplementalOxygen'`.

```sql
o2_delivery_device_1 IN
(
    'None'
)
```

Feeds `'None'`.

### Ventilator-mode sets (`ventilator_setting`)

The exact `ventilator_mode` set feeding the `'InvasiveVent'` branch is:

```sql
ventilator_mode IN
(
    '(S) CMV'
    , 'APRV'
    , 'APRV/Biphasic+ApnPress'
    , 'APRV/Biphasic+ApnVol'
    , 'APV (cmv)'
    , 'Ambient'
    , 'Apnea Ventilation'
    , 'CMV'
    , 'CMV/ASSIST'
    , 'CMV/ASSIST/AutoFlow'
    , 'CMV/AutoFlow'
    , 'CPAP/PPS'
    , 'CPAP/PSV'
    , 'CPAP/PSV+Apn TCPL'
    , 'CPAP/PSV+ApnPres'
    , 'CPAP/PSV+ApnVol'
    , 'MMV'
    , 'MMV/AutoFlow'
    , 'MMV/PSV'
    , 'MMV/PSV/AutoFlow'
    , 'P-CMV'
    , 'PCV+'
    , 'PCV+/PSV'
    , 'PCV+Assist'
    , 'PRES/AC'
    , 'PRVC/AC'
    , 'PRVC/SIMV'
    , 'PSV/SBT'
    , 'SIMV'
    , 'SIMV/AutoFlow'
    , 'SIMV/PRES'
    , 'SIMV/PSV'
    , 'SIMV/PSV/AutoFlow'
    , 'SIMV/VOL'
    , 'SYNCHRON MASTER'
    , 'SYNCHRON SLAVE'
    , 'VOL/AC'
)
```

The exact `ventilator_mode_hamilton` set feeding the same `'InvasiveVent'`
branch is:

```sql
ventilator_mode_hamilton IN
(
    'APRV'
    , 'APV (cmv)'
    , 'Ambient'
    , '(S) CMV'
    , 'P-CMV'
    , 'SIMV'
    , 'APV (simv)'
    , 'P-SIMV'
    , 'VS'
    , 'ASV'
)
```

The exact Hamilton set feeding the `'NonInvasiveVent'` branch is:

```sql
ventilator_mode_hamilton IN
(
    'DuoPaP'
    , 'NIV'
    , 'NIV-ST'
)
```

The order of the CASE branches is part of the source semantics and is the
priority `Tracheostomy` > `InvasiveVent` > `NonInvasiveVent` > `HFNC` >
`SupplementalOxygen` > `None`; a row matching multiple sets receives the first
status. Any row matching none receives NULL and is removed by `vd0`.

The derived status literals are not source filters, but the exact output values
are: `'Tracheostomy'`, `'InvasiveVent'`, `'NonInvasiveVent'`, `'HFNC'`,
`'SupplementalOxygen'`, `'None'`, and SQL NULL. The comment-only `T-piece`
literal is not executable and is not part of the code specification.

## Aggregations, windows, and temporal carry-forward

1. `tm` uses `UNION DISTINCT` over `(stay_id, charttime)`.
2. `vd0` uses three window functions:
   - `LAG(charttime, 1) OVER (PARTITION BY stay_id, ventilation_status ORDER BY charttime)`;
   - `LEAD(charttime, 1) OVER w`, with `w = (PARTITION BY stay_id ORDER BY charttime)`;
   - `LAG(ventilation_status, 1) OVER w`.
3. `vd1` computes `ventduration` with
   `DATETIME_DIFF(charttime, charttime_lag, MINUTE) / 60`, but this value is
   carried into `vd2` and never affects a filter, grouping, or final column.
4. `vd2` computes the running `SUM(new_ventilation_event) OVER
   (PARTITION BY stay_id ORDER BY charttime)` as `vent_seq`.
5. The final query groups by `(stay_id, vent_seq)` and computes `MIN(charttime)`,
   a conditional `MAX` for `endtime`, and `MAX(ventilation_status)`. It applies
   `HAVING MIN(charttime) != MAX(charttime)`.

There is no `AVG`, `COUNT`, `ARRAY_AGG`, explicit `ORDER BY` on the final
result, or source-value aggregation other than the listed `MIN`/`MAX`/`SUM`.

## Semantically essential inputs

These are source fields or discriminators whose values can alter inclusion,
episode identity, grouping, temporal carry-forward, or a clinically meaningful
output. They are descriptive source facts, not a terminal representability
decision.

- **`stay_id`**: joins each dependency to the unioned event grid; partitions
  every temporal window; defines the output scope and final grouping. Losing or
  changing it can merge or split patients' episodes.
- **`charttime`**: defines the `tm` distinct key and both join keys; orders all
  lag/lead/running-sum windows; controls the 14-hour break rules, `starttime`,
  `endtime`, and the final one-row-versus-multi-row `HAVING` decision. It is the
  essential temporal carry-forward input.
- **`o2_delivery_device_1`**: controls tracheostomy, endotracheal-tube, NIV,
  HFNC, supplemental-oxygen, and None classifications, in CASE priority order.
- **`o2_delivery_device_2`, `_3`, `_4`**: each can independently make a row
  `NonInvasiveVent`; omitting these slots changes classification.
- **`ventilator_mode`**: exact membership in the 36-value source set can make a
  row `InvasiveVent`.
- **`ventilator_mode_hamilton`**: exact membership in the 10-value invasive set
  or the 3-value NIV set can change classification. It is also used separately
  from `ventilator_mode`, despite the unused `COALESCE` debug alias.
- **`ventilation_status`**: the CASE discriminator controls the NULL-row
  exclusion, status-specific `charttime_lag`, status-change event boundaries,
  the episode sequence, the output category, and the final `MAX` status.
- **`new_ventilation_event` / `vent_seq`**: derived from the preceding fields;
  they control the interval grouping and are therefore part of the semantic
  natural grain even though `vent_seq` is not output.
- **Next-row temporal relation (`charttime_lead`)**: controls whether an
  episode ends at the next documented status time or at the current time after
  a terminal/14-hour gap.

The dependency `subject_id` is not consumed by this SQL and is not an output
key. The `vent_mode` alias and `ventduration` are selected/carried for debug or
intermediate bookkeeping but are dead with respect to the final result. The
source dependency fields for oxygen flows, numeric ventilator settings,
`ventilator_type`, `valueuom`, and `storetime` are likewise not consumed here.

## Notes and provisional fragment leads read

Read `mimic-iv/concepts_fhir/MIMIC_NOTES.md`, including the current entries on
itemid identity, chartevents categorical values, effective datetime handling,
opaque resource keys, and the 2026-08-21 UTC rebuild. The current notes say
that itemid-derived Observation codes retain exact source itemids, that
chartevents categorical text is in `valueString`, and that rebuilt-warehouse
datetime behavior must be checked rather than assuming the historical DST
shift. These are mapping/probing context; this source SQL itself consumes the
already-derived dependency columns.

The ventilation SQL itself names no FHIR coding-system URI and no itemid/ICD
coding system. The dependency probes identify the underlying chartevents system
as
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`; that
system applies to the dependency concepts' raw itemid observations, not to a
new code filter in ventilation. The fragments also report that served
`CodeSystem` resources are absent, so exact served coding system plus code—not
terminology expansion—is the relevant dependency-side discriminator.

The direct dependency leads read were:

- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/ventilator_setting.md`: issued/storetime
  coverage, absence of served CodeSystem resources, and the rebuilt
  `component.valueString` text for itemids `223848`, `223849`, and `229314`.
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/oxygen_delivery.md`: issued/storetime
  coverage and repeated same-item `226732` resources at one patient/time.

Those fragment entries are provisional leads, not established evidence for a
ventilation verdict. Their implications for this source contract are that the
two dependencies must preserve exact categorical text, their dependency-defined
ranking/aggregation, and charttime; ventilation must consume their named output
columns rather than infer them from resource identifiers or labels. A search of
the other `MIMIC_NOTES.d` fragments found no additional direct
`ventilation`/`oxygen_delivery`/`ventilator_setting` lead. No FHIR mapping or
ViewDefinition is authored here.

For shared ICU-chartevents context, the provisional `rrt.md`, `crrt.md`,
`vitalsign.md`, and `gcs.md` fragments were also read. They report repeated
same-item resources, historical/session-dependent datetime or `issued`
behavior, and superseded attempts to recover source values or times from opaque
resource IDs. They were treated only as leads; the current `MIMIC_NOTES.md`
UTC-rebuild guidance and opaque-ID policy take precedence. Ventilation does not
consume dependency `storetime`, and its source `charttime` remains essential
because it controls the event grid, ordering, episode grouping, and interval
boundaries.
