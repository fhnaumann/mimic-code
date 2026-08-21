Evidence block

Concept: `first_day_gcs`, attempt 0001.

Read `AGENTS.md`, `MIMIC_NOTES.md`, the source analysis, the canonical ViewDefinition, provisional `MIMIC_NOTES.d/gcs.md` and `first_day_vitalsign.md`, relevant ICU/vitals fragments, completed `gcs` attempt 0006, and the upstream `mimic-fhir` ETL SQL. Probed the authoritative Delta with embedded Pathling/Spark.

Mappings established:

- ICU Encounter stream, filtered by `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`; `subject.getReferenceKey(Patient)` joins to Patient identifier system `.../identifier/patient`, and Encounter ICU identifier carries `stay_id`.
- ICU Encounter `getResourceKey()` is emitted as `icu_encounter_key`; `period.start` is `intime_datetime`, parsed with `TRY_CAST(... AS TIMESTAMP_NTZ)`.
- Chartevents Observation code system is `http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-chartevents-d-items`; code carries itemid, Quantity value carries `valuenum`, `valueString` is the source-text path, and the Observation encounter reference joins to the ICU Encounter key.
- The target must consume completed dependency output `FROM gcs`, joining on `icu_encounter_key`; GCS is not rederived from FHIR. Dependency columns `gcs`, `gcs_motor`, `gcs_verbal`, `gcs_eyes`, and `gcs_unable` feed the target directly.

Authoritative demo counts: itemids `220739`, `223900`, `223901` had 3,274, 3,266, and 3,251 rows respectively; total 9,791 coding rows/resources (1:1). Effective dateTime, Quantity value, encounter reference, and patient reference were populated on all 9,791 rows. Period, instant, Quantity unit, and valueString were absent. ICU Encounter `(subject_id, stay_id, intime)` and source chartevents `(stay_id, charttime, itemid)` checks were 140/140 and 9,791/9,791; numeric Quantity values agreed 9,791/9,791.

Representability check: relational source had 1,348 `No Response-ETT` and 78 `No Response` rows, both with `valuenum=1`. Served verbal Observations had Quantity 1 for all 1,426 and no valueString, so the labels are indistinguishable; the Quantity-1 heuristic is only 94.53% accurate and is forbidden. A demo counterfactual replay changed first-day outputs on 43/140 `gcs_min`, 41/140 `gcs_verbal`, 6/140 `gcs_motor`, and 12/140 `gcs_eyes` rows. This is essential source loss evidence for the judge, not a terminal decision. Resource IDs were treated as opaque and not used for recovery.

The prober independently verified the provisional GCS and first-day chartevents leads and appended a dataset-wide finding to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_gcs.md` about chartevents dateTime-only representation and global ETL omissions. Carryover mapping was written and recorded at `mimic-iv/concepts_fhir/carryover/first_day_gcs/fhir-prober.md`. No immutable attempt artifact was edited.
