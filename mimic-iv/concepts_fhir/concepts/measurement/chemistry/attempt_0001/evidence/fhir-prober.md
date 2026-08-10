Evidence block — `chemistry`

Read `AGENTS.md`, `LOOP_CONTRACT.md`, `carryover/chemistry/source-analyst.md`, `MIMIC_NOTES.md`, all existing `MIMIC_NOTES.d` fragments, the canonical observation ViewDefinition, and upstream lab Observation, Specimen, and Encounter ETL SQL.

Mapped `mimiciv_hosp.labevents` to `Observation`, `labevents.specimen_id` through `Observation.specimen` to `Specimen`, Patient identifiers to `subject_id`, hospital Encounter identifiers to nullable `hadm_id`, Observation effective dateTime to `charttime`, lab code system `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-d-labitems`, Quantity value/unit/comparator, string fallback, and specimen identifiers. Confirmed the twelve active chemistry itemids: 50862, 50930, 50976, 50868, 50882, 51006, 50893, 50902, 50912, 50931, 50983, 50971; commented POC itemids are excluded. The output is specimen-level with `subject_id INTEGER`, nullable `hadm_id INTEGER`, `charttime TIMESTAMP`, `specimen_id INTEGER`, and twelve nullable `DOUBLE` analytes.

Demo probe findings: chemistry subset 26,767 FHIR rows and 26,763 source-qualified rows; all source-qualified rows had Quantity value/unit/effective datetime; four excluded rows materialized as comment-derived `valueString`; 3,289 distinct specimen groups matched the oracle; 21,521/26,763 rows had Encounter references and the remainder must retain typed NULL `hadm_id` rather than heuristic admissions; ten effective datetimes showed the known upstream DST-gap shift. `Observation.getResourceKey()` is not a relational key.

The prober independently checked the provisional `cardiac_marker` and `blood_differential` fragments and appended one dataset-wide finding to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/chemistry.md`: lab `Specimen.type.coding.display` is absent (0/11,122). `MIMIC_NOTES.md` was not edited. No implementation files were authored.

Carryover written and recorded: `mimic-iv/concepts_fhir/carryover/chemistry/fhir-prober.md`.
