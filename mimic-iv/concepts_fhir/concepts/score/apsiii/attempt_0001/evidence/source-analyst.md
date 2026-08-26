# Source analyst evidence

Concept: `apsiii`, attempt `0001`.

The source analyst read `mimic-iv/concepts/score/apsiii.sql` in full, checked the DAG node and SHA256, read the loop contract and MIMIC notes, inspected the oracle manifest, and reviewed the six completed dependency SQL definitions. The analysis identifies a one-row-per-`stay_id` output, manifest key `stay_id`, required resource-key columns, all source/dependency joins and temporal predicates, the ventilation/specimen and ICD-9/ICD-10 literals, score CASE rules, window/aggregate behavior, null handling, and essential inputs. Dependencies are `bg`, `first_day_gcs`, `first_day_lab`, `first_day_urine_output`, `first_day_vitalsign`, and `ventilation`; the candidate must consume their completed views rather than rederive them.

Reusable analysis was written to `mimic-iv/concepts_fhir/carryover/apsiii/source-analyst.md` and recorded with `mimic_utils carryover-record`. No ViewDefinition or `concept.sql` was authored by this stage.
