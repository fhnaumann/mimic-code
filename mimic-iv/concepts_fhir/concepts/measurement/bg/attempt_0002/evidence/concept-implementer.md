# Concept-implementer evidence — bg retry

**Attempt:** `measurement/bg/attempt_0002`.

Created all five ViewDefinitions and `concept.sql` in the new immutable
attempt. The implementation preserves attempt_0001's Patient, Encounter,
Specimen, lab/chart Observation projections, exact proprietary code filters,
specimen grouping, left Encounter joins, and 2-hour/4-hour SpO2/FiO2 windows.

Static validation passed: ViewDefinition JSON and filename/name labels are
valid; SQL parses as Spark SQL; all 27 manifest columns are present in order
with explicit casts; `fio2_chartevents` is FLOAT and `aado2_calc` is
DECIMAL(38,4); and no parameterless `VARCHAR` cast remains (`specimen` uses
`VARCHAR(255)`). No `unrepresentable.json` is required. Attempt_0001 was not
edited, no full gate was run, and no `MIMIC_NOTES.md` entry was added or
updated.
