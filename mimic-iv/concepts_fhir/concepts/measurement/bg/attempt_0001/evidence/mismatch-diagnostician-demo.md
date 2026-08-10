# Mismatch-diagnostician evidence — bg demo failure

The demo failed because Spark 4.0.2 rejects the parameterless cast at
`concept.sql:224`:

```sql
CAST(specimen AS VARCHAR) AS specimen
```

A complete search found only this executable bare-`VARCHAR` cast; none occur in
the five ViewDefinitions. The required fix is to create a new immutable attempt
with `CAST(specimen AS VARCHAR(255))`, leaving mappings, joins, filters,
timestamps, and terminology unchanged. This is an implementer-only fix, so no
carryover stage should be invalidated. No dataset-wide note should be added or
updated. No full-data divergence exists because execution stopped before output.
