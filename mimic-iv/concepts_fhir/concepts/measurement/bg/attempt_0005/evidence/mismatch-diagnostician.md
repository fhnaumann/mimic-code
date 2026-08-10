# Evidence: mismatch-diagnostician (`bg`, attempt_0005)

The full result is correctly `review`, tier `contested`, classification
`unavailable_no_key`, not a machine `mismatch`. Schema and row count both pass;
the 511,637 `only_candidate` and 511,637 `only_oracle` rows are the two sides
of an unkeyed `EXCEPT ALL`, so they do not mean every row was invented.

Diagnosis: fixable implementer SQL regression. The outer projection at
`attempt_0005/concept.sql:215` uses:

```sql
CAST(charttime AS TIMESTAMP) AS charttime
```

It must remain `CAST(charttime AS TIMESTAMP_NTZ) AS charttime`. The internal
extractions already use `TIMESTAMP_NTZ`; the outer timezone-bearing cast shifts
every wall-clock value and changes every full tuple. Attempt 0003's successful
expression and demo multiset comparison confirm that the other 26 columns are
not implicated. Retry with only this attempt-scoped SQL correction. Do not
invalidate either carryover stage.

The residual expected after this fix is a small intrinsic transformation gap,
not justification for accepting attempt 0005: `mimic-fhir/sql/fhir_observation_labevents.sql:15`
and `:121`, `fhir_observation_chartevents.sql:9` and `:67`, and
`fhir_specimen_lab.sql:18` and `:58` cast source chart times through
`TIMESTAMPTZ`, irreversibly normalizing DST-gap wall times. The comments fallback
at `fhir_observation_labevents.sql:133-136` is separately handled by the
attempt's `NULLIF(value_string, '___')`. These citations should reach the judge
only after the table-wide timezone bug is fixed.

No `MIMIC_NOTES.md` entry was added or updated. No files were modified and no
additional HPC run was launched during diagnosis.
