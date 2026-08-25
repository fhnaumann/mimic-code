Evidence block — fhir-prober

The prober read AGENTS.md, fhir-mapping guidance, the canonical SQL, reused
source analysis, MIMIC_NOTES.md, and all MIMIC_NOTES.d fragments. It rechecked
the reopened mapping against embedded Pathling 9.6.0/Spark 4.0.2 over the
authoritative demo Delta without parsing or reconstructing resource IDs.

The source table maps to Observation. Subject and ICU-stay identifiers are
obtained from Patient/Encounter identifier.value and joined through opaque
reference keys. Chartevents item codes use the exact proprietary system
http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items. Effective
dateTime is extracted from effective.ofType(dateTime); Quantity values are
cast before numeric cleaning; null-valuenum text uses value.ofType(string).
The reopened upstream fix is represented by component.value.ofType(string)
under forEachOrNull component, with component code/system paths.

The target had 14,831 rows. Code, resource key, references, effective time,
issued, coding system, and display were populated 14,831/14,831; Quantity
values were present on 14,408 rows, direct strings on 423, and component text
on 2,319. Component coverage was 906/1,292 for item 223848, 1,011/1,048 for
223849, and 402/402 for 229314. Text pivots agreed exactly on 2,742/2,742
rows; cleaned numeric aggregates agreed within 1e-6 on all 14,831 groups; and
the effective-key multiplicities and issued/storetime checks were exact. No
current DST divergence was observed.

The prober appended the dataset-wide rebuilt-chartevents component finding to
mimic-iv/concepts_fhir/MIMIC_NOTES.d/ventilator_setting.md and updated the
mutable carryover mapping at
mimic-iv/concepts_fhir/carryover/ventilator_setting/fhir-prober.md.
