# Demo runner evidence

`uv run mimic_utils validate-demo norepinephrine_equivalent_dose` froze the
attempt and the embedded Pathling-on-Spark demo run was then executed.

The run did not execute SQL. Artifact discovery aborted because the attempt
contained no `ViewDefinition.*.json` file: `No ViewDefinition.*.json in .../attempt_0001 — nothing to register`.
Consequently no candidate columns, types, row count, `candidate.demo.parquet`,
or `shape.demo.json` were produced. This is an execution/shape failure, not a
row-count result; row count is non-gating, but an execution failure cannot
proceed to full data.

The implementer had treated the concept as dependency-only (`concept.sql`
selects from the completed `vasoactive_agent` view), so the next diagnosis must
determine the smallest valid artifact fix without rewriting this immutable
attempt. No candidate artifact was modified and no commit was made.

Artifact: this evidence file; no runner output artifact was produced.
