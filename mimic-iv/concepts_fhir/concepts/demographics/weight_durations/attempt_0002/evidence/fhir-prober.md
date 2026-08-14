# FHIR-prober carryover evidence

Attempt 0002 reused the validated FHIR mapping from `mimic-iv/concepts_fhir/carryover/weight_durations/fhir-prober.md`, as reported by `uv run mimic_utils carryover weight_durations`. The prior probe established the exact coding, identifier, datetime, Quantity, multiplicity, and upstream DST behavior; no mapping-stage invalidation was diagnosed, so no FHIR-prober subagent was re-run.
