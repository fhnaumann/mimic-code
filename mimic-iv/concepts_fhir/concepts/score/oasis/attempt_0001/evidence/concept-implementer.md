# Concept-implementer evidence

Concept: `oasis`; attempt: `0001`.

The implementer read both reusable analyses, the curated notes and relevant
fragments, the oracle manifest, the completed dependency output schemas, and
the ViewDefinition/embedded-Spark authoring conventions. It authored the
following immutable artifacts:

- `ViewDefinition.patient.json`
- `ViewDefinition.hospital_encounter.json`
- `ViewDefinition.hospital_service.json`
- `ViewDefinition.icu_encounter.json`
- `concept.sql`

The candidate consumes the five dependency stems through opaque encounter-key
joins, preserves the source score thresholds, null handling, first-day and
inclusive ventilation windows, representative-value branches, score sum, and
logistic probability, and emits the 25 oracle columns plus the three required
opaque resource-key columns with manifest-compatible casts. MIMIC identifiers
come from `identifier.value`; resource keys are used only as opaque equality
joins and outputs. The service/admission-type limitation is represented using
the available `AMB` class plus surgical service coding approximation; no
false unrepresentability declaration was added and no terminal decision was
made.

`uv run mimic_utils lint-sql oasis` completed cleanly. No dataset-wide finding
was appended to `MIMIC_NOTES.d/oasis.md` by this stage. No state transition,
execution, or commit was performed.
