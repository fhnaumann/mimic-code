Final evidence block — concept `acei`.

Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the equivalence judge
after full-data review. Converged attempt: `attempt_0004`.

Full runs consumed: **2** (attempt_0003 job `29599602`; attempt_0004 job
`29599959`). Attempt 0003 exposed and diagnosed a fixable omission of
medication-mix ingredient references. Attempt 0004 added the ingredient branch
with `UNION ALL` and restored exact source multiplicity.

Final full-data artifacts:

- `comparison.full.json`
- `run_meta.full.json`
- `candidate.demo.parquet`
- `shape.demo.json`
- `submit.slurm`
- `hpc_job.json`
- all five ViewDefinitions and `concept.sql`

Final schema matched exactly. Oracle and candidate row counts both equal
112,014 (reported, not the correctness gate). The unkeyed full-tuple diff is
`review`, tier `contested`, classification `unavailable_no_key`, with 9,073
only-oracle and 9,073 only-candidate paired substitutions. The judge accepted
these as intrinsic upstream FHIR loss: invalid/incomplete validity periods are
omitted by `mimic-fhir/sql/fhir_medication_request.sql:172-177`, and DST-gap
timestamps are irreversibly normalized through `TIMESTAMPTZ` at lines 43-44;
`authoredOn` is pharmacy entry time and cannot recover the source endpoints.
Descriptive exact multiset overlap was 102,941/112,014 (91.9001%); no
representable_fraction was emitted for the unkeyed comparison.

MIMIC_NOTES.md entries added or updated by this concept:

- Added **Spark requires a length for VARCHAR casts**.
- Added and then sharpened **Prescription Medication.code prefers
  NDC/formulary; the source drug name is in an identifier**, including the
  medication-mix ingredient mapping and multiplicity.
- Added and updated **MedicationRequest omits invalid or incomplete
  prescription validity periods**.
- Existing **FHIR datetimes carry an offset — cast to TIMESTAMP_NTZ, never to
  TIMESTAMP** was updated with acei full-data evidence.

No divergent dependencies. No commit was made.
