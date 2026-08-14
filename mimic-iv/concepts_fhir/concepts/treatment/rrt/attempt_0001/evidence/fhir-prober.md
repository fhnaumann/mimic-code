## Evidence

The FHIR prober read the source carryover, curated notes, and relevant
provisional fragments, then probed authoritative Delta tables. It mapped
chartevents to `Observation`, inputevents to ICU `MedicationAdministration`,
procedureevents to ICU `Procedure`, and joined ICU stays through
`Encounter.identifier` and patients through references. It confirmed the
literal code systems and itemids, including executable source code `227525`,
and checked interval endpoints, value[x], effective/performed variants, and
typed identifier outputs without parsing resource ids.

The prober recorded `mimic-iv/concepts_fhir/carryover/rrt/fhir-prober.md` and
appended a dataset-wide finding to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/rrt.md`:
repeated same-item chartevents at one stay/time are retained. Its read-only
overlay check found 5,124 reconstructed candidate tuples versus 5,134 oracle
tuples, with 10 oracle-only tuples, before implementation.
