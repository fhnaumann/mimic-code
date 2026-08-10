# Evidence: mismatch-diagnostician (`bg`, attempt_0004)

The demo gate failed before candidate output or shape comparison. Diagnosis:
fixable implementer SQL bug. Spark 4 rejects the unsized cast at
`concept.sql:216`:

```sql
CAST(specimen AS VARCHAR) AS specimen
```

The minimal correction for a new immutable attempt is
`CAST(specimen AS VARCHAR(255)) AS specimen`. The manifest requires a VARCHAR
specimen and the source value is limited to 200 characters. No ViewDefinition
or mapping change is required, and no carryover stage is invalidated: the fault
is attempt-scoped SQL typing only.

Inspected `AGENTS.md`, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, all attempt 0004
implementation and evidence artifacts, both `bg` carryover analyses, the oracle
manifest entry, and the prior successful attempt's sized cast. No dataset-wide
quirk was added or updated. No HPC run was launched.
