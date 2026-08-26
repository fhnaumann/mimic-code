## FHIR prober evidence

The prober read the source carryover, curated `MIMIC_NOTES.md`, and relevant
provisional fragments, then checked authoritative demo Delta data through
embedded Pathling/Spark. It mapped the raw ICU spine to `Encounter`: the ICU
identifier system is
`http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`, with
`identifier.value` as the string `stay_id`; `getResourceKey()` is the opaque
`icu_encounter_key`; `subject.getReferenceKey(Patient)` is the patient key;
`partOf.getReferenceKey(Encounter)` resolves the parent admission; and
`period.start`/`period.end` carry ICU `intime`/`outtime`.

Dependency interfaces were mapped without re-deriving them: Observation
dependencies use `subject.getReferenceKey(Patient)`,
`encounter.getReferenceKey(Encounter)` where present, `specimen` references,
effective dateTime/Period variants, and Quantity/string values; ICU
MedicationAdministration dependencies use `subject`, `context` (not
`encounter`) reference keys, effective Period/dateTime variants, and dosage
rate/dose Quantity values. SOFA must consume completed dependency temp views
and preserve nullable lab encounter joins. `bg`'s completed output supplies the
literal `ART.` specimen filter and P/F ratio; ventilation supplies the exact
`InvasiveVent` status filter.

Checks included 140/140 ICU Encounters with identifiers, keys, parent links,
and period endpoints; 15,615/15,615 `icustay_hourly` tuples; 889 blood-gas
rows (706 `ART.`, 563 non-null P/F ratios); 209 ventilation rows (61 invasive);
and target medication counts of dobutamine 44, dopamine 28, epinephrine 36,
and norepinephrine 947. Exact system+code discrimination was confirmed; no
SOFA-specific essential representation loss was found. Quantity aliases and
datetime variants require the casts and COALESCE patterns documented in the
curated notes.

Dataset-wide findings appended by the prober to the owned fragment are that
ICU Encounter period endpoints are direct populated dateTime fields, and ICU
MedicationAdministration links the Encounter through `context`, not
`encounter`. See `mimic-iv/concepts_fhir/MIMIC_NOTES.d/sofa.md`.

Artifacts: `mimic-iv/concepts_fhir/carryover/sofa/fhir-prober.md`, its recorded
carryover ledger, the owned notes fragment, and this evidence file. No
ViewDefinition or `concept.sql` was authored.
