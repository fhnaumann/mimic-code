# FHIR prober evidence

Concept: `apsiii`, attempt `0001`.

The prober read the source/carryover analysis, LOOP_CONTRACT.md, curated notes, and relevant provisional fragments, and probed the authoritative demo Delta with embedded Pathling 9.6.0/Spark 4.0.2 in UTC plus the read-only demo oracle. It mapped the ICU Encounter/Patient/hospital Encounter identifier and opaque resource-key spine, hospital-linked Condition coding, and the six completed dependency interfaces. It confirmed the proprietary ICD-9/ICD-10 MIMIC diagnosis systems and exact CKD prefixes, hospital-linked Condition recovery 4,506/4,506, ICU spine 140/140, dependency columns/types, and the required typed casts and `TIMESTAMP_NTZ` handling.

The prober found the served `first_day_gcs` interface has `gcs_unable` NULL on all 140 demo stays while the source has 23 stays with `gcs_unable=1`; the loss changes GCS components and can affect clinically meaningful `gcs_score`, `apsiii`, and `apsiii_prob`. It did not make a terminal decision; the judge must assess whether this is inherited from the completed dependency and whether it blocks. The 52 missing `bg` hospital keys coincide with source-null `hadm_id` rows already excluded by APS III's source inner join. No resource IDs were parsed or used as semantic side channels.

Reusable mapping was written to `mimic-iv/concepts_fhir/carryover/apsiii/fhir-prober.md` and recorded with `mimic_utils carryover-record`. A dataset-wide diagnosis-system finding was appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/apsiii.md`; `MIMIC_NOTES.md` was not edited. No ViewDefinition or `concept.sql` was authored.
