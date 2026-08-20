# Evidence — hpc-poller

Concept `nsaid`, attempt `0002`; Slurm job `30231253`.

The sanctioned poll/fetch completed successfully and verified fresh
`comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json`.
Comparator verdict: `review`, tier `gap_shaped`, classification
`paired_residual`; `judge_required=true` and `diagnostician_required=false`.

The schema matched with seven columns including the declared opaque key columns
`patient_key` and `encounter_key`. Oracle and candidate row counts were both
235,678 (reported only), with 225,384 identical rows (95.63%). The residual
paired 1:1 on `(hadm_id, nsaid, subject_id)`:

- `differing_null_only`: 10,276 rows, candidate validity endpoints absent
  where the oracle has values (`starttime` null on 10,276; `stoptime` null on
  10,249), a missing FHIR validity-period representation.
- `differing_conflict`: 18 rows, fully attributed by the comparator to the
  upstream `TIMESTAMPTZ` DST cast (`starttime` 12; `stoptime` 6), with zero
  residual attribution rows.

No contested, unresolvable, blocking, or declaration contradiction was found.
The attributed conflict citations include
`mimic-fhir/sql/fhir_medication_request.sql:43-44`; the judge must confirm that
the cited ETL writes the sourced FHIR element and that the 18/235,678 fraction
fits DST-gap rarity. The diagnostician is skipped solely because the comparator
already proved the attribution over every conflict.

Artifacts:
- `comparison.full.json`
- `run_meta.full.json`
- `hpc_accounting.json`
