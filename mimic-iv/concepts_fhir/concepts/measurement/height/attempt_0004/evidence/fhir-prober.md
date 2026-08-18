# FHIR-prober evidence (reused carryover)

The FHIR mapping was reused from
`mimic-iv/concepts_fhir/carryover/height/fhir-prober.md` because the served
warehouse mapping is unchanged. It maps the two exact item codes under the
MIMIC chartevents coding system, joins Observation references to Patient and
ICU Encounter resource keys, obtains numeric identifiers from the required
identifier systems, and reads `effective.ofType(dateTime)` directly.

The mapping explicitly rejects resource-id inference, uses direct
`TIMESTAMP_NTZ` handling, casts materialized Quantity values before arithmetic,
and preserves the source full-outer join. The prior effective-choice probe
confirmed the target stream uses dateTime rather than Period or instant.

Artifact read: `mimic-iv/concepts_fhir/carryover/height/fhir-prober.md`.
