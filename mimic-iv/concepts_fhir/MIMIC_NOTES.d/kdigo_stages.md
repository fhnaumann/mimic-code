## Normalized dependency times propagate through relative-time stage windows

- Affected: `Observation.effectiveDateTime` from labevents, outputevents, and chartevents; ICU `Encounter.period.start`; dependent concepts that join those streams on time or window by elapsed time from ICU admission.
- Verified: `kdigo_stages` attempt_0001 full-data review had 1,707 oracle-only and 1,464 candidate-only multiset rows. Full-oracle replay found 145 selected `kdigo_creatinine` times, 393 selected `kdigo_uo` times, 26 retained CRRT times, and 10 ICU `intime` values moved by the New York spring-forward normalization. Their direct prior-window/event-axis reach covered 1,653 oracle and 1,399 candidate residual rows; another 43 oracle and 44 candidate same-key rows differed only in `aki_stage_smoothed`, consistent with the concept's subject-partitioned six-hour window over elapsed time. Nine rows per side paired within numeric tolerance, while one non-DST `uo_rt_24hr` rounding pair remained a fixable dependency residual rather than DST attribution.

## BigQuery `NUMERIC` is `DECIMAL(38,9)` — a port that widens the intermediate scale double-rounds away from the oracle

Supersedes the final sentence of the entry above: the `uo_rt_24hr` pair it called
a "fixable dependency residual" was not a rounding error in the dependency's
algorithm but a decimal-scale mismatch in its port, since corrected.

`ROUND(CAST(x AS NUMERIC), n)` in a canonical query does **two** roundings, and
the first one is invisible. `mimic_utils.transpile` (sqlglot `bigquery` →
`duckdb`) maps BigQuery `NUMERIC` to `DECIMAL(38,9)`, so the oracle quantizes the
intermediate to nine decimals before the explicit `ROUND` sees it. A port that
casts the same expression to a *wider* scale skips that quantization and can
round the other way at a half-way boundary. The wider scale is not the safer
choice it looks like: it is a different computation.

- Affected: every ported `concept.sql` whose canonical uses `CAST(... AS NUMERIC)`
  — `bg`, `blood_differential`, `first_day_height`, `height`, `icustay_detail`,
  `kdigo_uo`, `meld`, `norepinephrine_equivalent_dose`, `urine_output_rate`,
  `vitalsign`, `weight_durations`. Match `DECIMAL(38,9)` exactly; never widen it.
- Verified: `kdigo_uo` attempts 0001–0003 cast the `uo_rt_*` ratio to
  `DECIMAL(38,12)` (`attempt_0003/concept.sql:107,118,129`) against canonical
  `mimic-iv/concepts/organfailure/kdigo_uo.sql:84,90,97`. On `stay_id` 31463721,
  `charttime` 2174-05-12 20:40 (urineoutput 70, weight 84, `uo_tm_24hr`
  26.666667), DuckDB gives
  `ROUND(CAST(70.0/84.0/26.666667 AS DECIMAL(38,9)), 4) = 0.0313` but
  `... AS DECIMAL(38,12)), 4) = 0.0312`: scale 9 snaps 0.0312499996 to exactly
  0.03125, which the half-up round then lifts. Changing the six sites to
  `DECIMAL(38,9)` in attempt_0004 moved exactly one row and one column —
  `comparison.full.json` `diff.identical` 3,320,293 → 3,320,294,
  `diff.differing` 1,062 → 1,061, `columns_conflicting.uo_rt_24hr` 276 → 275,
  every other column, `only_oracle` (393), `only_candidate` (157) and the −236
  row delta unchanged. Output schema was unaffected: the outer casts to
  `DECIMAL(38,4)`/`DECIMAL(38,6)` absorb the intermediate scale.
- Note: dividing by an *un*rounded duration also yields 0.0313 here and is the
  wrong fix — canonical `kdigo_uo.sql:53,60,67` rounds `uo_tm_*` to six decimals
  in `uo_stg2` and lines 84–97 divide by that rounded column. Preserve it.

## Correction: the `kdigo_stages` DST residual closes at 0/0 once the dependency scale is fixed

Supersedes the verification numbers in the first entry, which were taken from
`attempt_0001` and are superseded by the full run of `attempt_0002`. The
mechanism described there — normalized dependency times propagating through
relative-time stage windows — stands unchanged; only the counts and the residual
move.

- Affected: as the first entry.
- Verified: `kdigo_stages` attempt_0002, built on `crrt` 0007,
  `kdigo_creatinine` 0002 and `kdigo_uo` 0004, had 1,703 oracle-only and 1,460
  candidate-only multiset rows (from 1,707/1,464 at attempt_0001; the −243 row
  delta is unchanged). The same 574 shifted inputs closed 1,697/1,703 and
  1,454/1,460; six per side paired within comparator tolerance, leaving
  **semantic residual 0/0** where attempt_0001 left nine in tolerance and one
  unattributed. Four pairs per side moved to exact — the one corrected
  `uo_rt_24hr` row plus three formerly inside tolerance — consistent with a
  single upstream correction reaching several stage rows through
  `aki_stage_uo` and the subject-partitioned six-hour smoothing window. The
  judge accepted on that basis with no human override.
