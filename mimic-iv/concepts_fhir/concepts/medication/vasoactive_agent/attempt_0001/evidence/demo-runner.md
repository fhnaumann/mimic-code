# Demo runner evidence

**Concept:** `vasoactive_agent`
**Attempt:** `attempt_0001`
**Verdict:** **`shape_ok`** — official gate verdict `shape_ok` (overall "MAY PROCEED TO FULL DATA"), exit status 0.

**Execution:** Succeeded. The embedded Pathling-on-Spark engine (no HTTP server) acquired the Spark lease, preprocessed dependencies in DAG order (registered views: `dobutamine`, `dopamine`, `epinephrine`, `milrinone`, `norepinephrine`, `phenylephrine`, `vasopressin`, `encounter_icu`, `medication_administration`), ran the ViewDefinition(s) + `concept.sql`, and wrote the Parquet candidate. No error output.

**Column-name comparison:** Matching / missing — all 10 oracle columns present:

- Oracle `expected_columns` (from `oracle_manifest.full.json`): `stay_id`, `starttime`, `endtime`, `dopamine`, `epinephrine`, `norepinephrine`, `phenylephrine`, `vasopressin`, `dobutamine`, `milrinone`
- Candidate `actual_columns` (12): those 10 exactly, plus `icu_encounter_key`, `patient_key`
- `missing_columns: []`. The 2 extra columns are the manifest's declared `key_columns` / `required_key_columns` (`icu_encounter_key`, `patient_key`) — the FHIR identity columns the candidate carries for the keyed diff, not divergences from the oracle shape. These were reported as `extra_columns` in the schema detail but `unexpected_columns: []` and `match: true`.

**Type comparison:** `incompatible_types: []`. All compatible: `stay_id` INTEGER↔int, `starttime`/`endtime` TIMESTAMP↔timestamp_ntz, and all seven agent columns (dopamine, epinephrine, norepinephrine, phenylephrine, vasopressin, dobutamine, milrinone) FLOAT↔float. Notably `milrinone` typed as `float` (not the all-null `SMALLINT`/`JSON` hazard) — so even its null-only column carries a correct numeric type.

**Row count (observation, NOT gated):** 1,874 candidate demo rows. Oracle full-data row count reported as 665,529. Candidate row count is non-gating per contract.

**Artifacts produced:**

- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/candidate.demo.parquet`
- `mimic-iv/concepts_fhir/concepts/medication/vasoactive_agent/attempt_0001/shape.demo.json` (verdict `shape_ok`, `executed: true`, `match: true`)

No implementation artifacts were modified, no state transitions beyond `run-demo`'s own scope were made, and nothing was committed.
