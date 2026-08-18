# Equivalence judge evidence — coagulation attempt 0005

Read `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, the current comparison and run
artifacts, current ViewDefinitions and SQL, and the full comparison history for
attempts 0002–0005. `divergent_dependencies` returned `[]`. The comparator's
`attributed` proof was used directly; no diagnostician was required or
spawned.

Verdict: `accept`.

The only divergence is 115 `differing_conflict` rows on `charttime`, with zero
only-oracle, only-candidate, or null-only rows. The exhaustive comparator replay
matched all 115 candidate values to the America/New_York `TIMESTAMPTZ`
round-trip, with zero residual. The relevant upstream statements are
`mimic-fhir/sql/fhir_observation_labevents.sql:15,121`, which cast and write
`Observation.effectiveDateTime`, and
`mimic-fhir/sql/fhir_specimen_lab.sql:18,58`, which writes the corresponding
normalized specimen collection time. The 115/1,543,003 fraction (0.00745%) is
consistent with the rare DST spring-forward gap, and the original wall time is
not present in served FHIR. Under the contract this proven upstream
transformation is accepted, not blocked.

Fidelity is 1,542,888/1,543,003 identical (99.9925%); no columns were excluded.
Artifacts assessed include:
`mimic-iv/concepts_fhir/concepts/measurement/coagulation/attempt_0005/comparison.full.json`,
`run_meta.full.json`, `hpc_accounting.json`, the current ViewDefinitions and
`concept.sql`, and prior comparison artifacts.
