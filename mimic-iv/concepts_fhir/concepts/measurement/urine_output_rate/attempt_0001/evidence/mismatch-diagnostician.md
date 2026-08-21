# Mismatch-diagnostician evidence — `urine_output_rate`

The diagnostician read the full comparison, candidate SQL/ViewDefinitions,
canonical SQL, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, and the completed
dependency attempt artifacts. The residual 335,779 conflicts are a fixable
attempt-scoped semantic bug, not an intrinsic FHIR gap and not a dependency
join failure.

Canonical `DATETIME_DIFF(..., HOUR)` counts crossed hour boundaries. Attempt
0001 uses raw Spark `TIMESTAMPDIFF(HOUR, start, end)` at
`concept.sql:77,86,96,105`, which counts only complete elapsed hours. A
05:59-to-11:00 interval therefore crosses six hour boundaries (excluded by
canonical `<= 5`) while raw Spark `TIMESTAMPDIFF` returns five (incorrectly
included). This explains the dominant 6-/12-hour volume, elapsed-time, and
rate conflicts across non-DST months; 24-hour/weight differences are small
inherited dependency/upstream timing effects.

The opaque dependency-key joins at `concept.sql:53-54` and `143-147` are
correct, and the completed `urine_output` attempt has the same small inherited
DST footprint. Source and FHIR carryover analyses remain valid; no carryover
stage should be invalidated and no notes fragment was appended.

Required remedy: create attempt 0002 and replace all four short-window hour
tests with boundary-counting logic equivalent to
`TIMESTAMPDIFF(HOUR, DATE_TRUNC('HOUR', start), DATE_TRUNC('HOUR', end))`,
without changing ViewDefinitions, dependency joins, or the 23-hour self-join.
