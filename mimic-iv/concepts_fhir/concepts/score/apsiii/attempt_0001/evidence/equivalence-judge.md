# Equivalence judge evidence

Concept: `apsiii`, attempt `0001`.

The independent judge read the full comparison, canonical APS III SQL, attempt artifacts/evidence, LOOP_CONTRACT.md, curated MIMIC_NOTES.md, and the divergent dependency states/evidence. It ruled `bug` on the `gap_shaped` review, not because APS III's scoring SQL is wrong, but because the sole divergence is inherited from the accepted `first_day_gcs` dependency and that dependency's historical missing discriminator is now representable in the rebuilt warehouse.

Comparator facts: schema matched; 73,181 candidate and oracle rows; 62,892 identical; 10,289 `differing_null_only` rows solely on `gcs_score`; zero conflicts, missing rows, or candidate-only rows. The candidate correctly preserves the canonical GCS scoring and final `COALESCE(gcs_score, 0)`. The stale dependency mapped numeric item `223900` without the now-available `Observation.component.where(code.coding.code='223900').valueString` carrier. The judge cited `mimic-fhir/sql/fhir_observation_chartevents.sql:97-113` and the current rebuilt warehouse, contrasted with the historical `:69-80`, and concluded that “all defensible mappings tried” is false for the dependency. `first_day_vitalsign` was divergent but introduced no APS III diff.

No diagnostician was spawned because the comparator set `diagnostician_required=false` and the judge's diagnosis was already specific. The judge found no APS III-owned mapping defect and no new dataset-wide quirk. This attempt cannot be accepted or blocked; the dependency `first_day_gcs` requires human reopening/re-authoring before APS III can be retried.
