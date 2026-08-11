## Evidence

Attempt 0004 created fresh `ViewDefinition.crrt_observation.json`,
`ViewDefinition.crrt_encounter.json`, and `concept.sql`. The implementation
reuses the diagnosed UUID-based recovery of pre-TIMESTAMPTZ charttime and uses
`CAST(timestamp AS STRING)` rather than `DATE_FORMAT` when reconstructing UUID
names. It preserves the exact CRRT item filters, repeated item 224146 rows,
ICU Encounter identifier join, 24 manifest-ordered output columns, and explicit
Spark-compatible casts.

The implementer read the canonical SQL, CRRT carryover analyses, curated notes,
CRRT fragment, and prior attempts 0001–0003. Structural validation passed for
the JSON, manifest shape, UUID recovery, filters, join, bounded VARCHAR casts,
and absence of `DATE_FORMAT`. No unrepresentable declaration was needed and no
new dataset-wide note was found.

Artifacts: `ViewDefinition.crrt_observation.json`,
`ViewDefinition.crrt_encounter.json`, and `concept.sql` in this attempt.
