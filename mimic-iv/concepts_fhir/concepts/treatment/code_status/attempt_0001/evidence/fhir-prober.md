# FHIR prober evidence — code_status attempt 0001

The ICU `chartevents` branch maps to `Observation`; the selected hospital POE
code-status branch has no exact served FHIR resource. The probe used embedded
Pathling 9.6.0 on Spark 4.0.2 over `/Users/nau025/warehouses/mimic-iv-demo/delta`
and read-only DuckDB over `/Users/nau025/warehouses/mimic4-demo.db`.

For chart events, filter `code.coding.system` to
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items` and exact
code `223758`, then extract `value.ofType(string)`,
`(effective).ofType(dateTime)`, and the Patient/ICU Encounter identifier spine.
The Patient and Encounter identifiers are strings and require final integer
casts; UUID/reference keys are join-only. The ICU Encounter's `partOf` links to
the hospital Encounter for `hadm_id`. Datetimes require `TIMESTAMP_NTZ`.

Demo results: the target chart code returned 147 rows, display `Code Status`,
and exact status counts: `Full code` 139, `Comfort measures only` 1,
`DNI (do not intubate)` 1, `DNR / DNI` 3, and `DNR (do not resuscitate)` 3.
The chart projection matched the DuckDB source as an exact 147-row multiset,
including patient, hospital admission, ICU stay, timestamp, and flags.

The POE selector returned 242 rows in the relational demo source. The served
MedicationRequest POE identifier stream had zero intersection with those 242
code-status POE IDs, so `MedicationRequest` fields must not be substituted for
POE event values or times. The POE branch is therefore an intrinsic coverage
gap; preserve full-tuple multiplicity and do not invent a natural key. The
oracle manifest specifies eight output columns, no natural key, and
`full_tuple_multiset` comparison over 269,072 rows.

The reusable mapping is recorded at
`mimic-iv/concepts_fhir/carryover/code_status/fhir-prober.md`. The prober also
appended two dataset-wide findings to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/code_status.md`: chartevents excludes one
hard-coded duplicate and excludes NULL-valued rows. Neither affected this
concept's 147-row demo target. `MIMIC_NOTES.md` was not edited.

Files read included `AGENTS.md`, `fhir-mapping/SKILL.md`, the shared notes and
all existing fragments, source analysis, source SQL, oracle manifest,
`LOOP_CONTRACT.md`, canonical Observation ViewDefinition, and chartevents and
MedicationRequest ETL SQL.

Artifacts produced:
- `mimic-iv/concepts_fhir/carryover/code_status/fhir-prober.md`
- `mimic-iv/concepts_fhir/carryover/code_status/carryover.json`
- `mimic-iv/concepts_fhir/MIMIC_NOTES.d/code_status.md`
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0001/evidence/fhir-prober.md`
