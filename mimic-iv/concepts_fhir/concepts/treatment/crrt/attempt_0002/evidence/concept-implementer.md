## Evidence

Attempt 0002 was authored from the reusable CRRT source and FHIR analyses,
prior attempt, canonical SQL, manifest, and curated notes. It created fresh:

- `ViewDefinition.crrt_observation.json`
- `ViewDefinition.crrt_encounter.json`
- `concept.sql`

The retry retains the Observation resource ID through typed rows and
recomputes the upstream UUIDv5 relation for the served charttime and exactly
one hour earlier. It shifts only when the resource ID proves the earlier
pre-normalization charttime, leaving genuine 03:xx observations unchanged.
The existing exact item filters, ICU Encounter join, 24 output columns,
values, pivot, repeated-item preservation, and explicit casts remain intact.
No unrepresentable column was identified. No notes or carryover files were
modified by the implementation stage.
