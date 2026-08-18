Reused carryover evidence for `cardiac_marker`, attempt `0005`.

The FHIR mapping was reused from `mimic-iv/concepts_fhir/carryover/cardiac_marker/fhir-prober.md` (recorded from attempt 1). It maps numeric labevent Observations by the exact `mimic-d-labitems` system and string codes, joins Patient/Encounter/Specimen through opaque reference keys, emits identifier values as integer MIMIC columns plus required prefixed resource keys, uses a LEFT hospital Encounter join, groups by specimen identifier, and preserves FHIR datetimes with `TIMESTAMP_NTZ`. The probe recorded 386 numeric observations, 283 specimen groups, exact grouped values, and two known DST-gap charttime divergences.

Artifact read: `mimic-iv/concepts_fhir/carryover/cardiac_marker/fhir-prober.md`.
