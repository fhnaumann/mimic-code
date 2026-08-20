# Evidence: source-analyst reuse (`first_day_bg`, attempt 0002)

The source analysis was reused from the registered carryover at
`mimic-iv/concepts_fhir/carryover/first_day_bg/source-analyst.md` rather than
re-run. It covers the canonical `firstday/first_day_bg.sql`, its `bg`
dependency, inclusive `intime - 6 hours` through `intime + 1 day` window,
stay-level grouping, and the 44-column output contract.

The reopened attempt preserves that analysis and adds only the required opaque
resource-key output columns; it does not rederive the dependency.

Artifacts read: `carryover/first_day_bg/source-analyst.md` and the canonical
source SQL. No new source-stage artifact was produced.
