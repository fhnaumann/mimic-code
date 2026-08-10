# Final evidence — antibiotic

- Attempt: `attempt_0001`.
- Demo: Spark shape gate `shape_ok`; all seven columns and types matched. Demo row count was 903 and was not used as a correctness gate.
- Full runs consumed: **1 of 10**.
- Full outcome: HPC job `29603036` completed; schema matched and full row count was 735,462 on both sides. Comparator verdict was `review`, `full_tuple_multiset`, `unavailable_no_key`.
- Divergence: 43,576 mirrored `only_candidate`/`only_oracle` tuples (5.925%). Exhaustive pairing attributed 43,453 to missing invalid/incomplete `MedicationRequest.dispenseRequest.validityPeriod.start/end` and 123 to irreversible `TIMESTAMPTZ` rewriting at `mimic-fhir/sql/fhir_medication_request.sql:43-44`; no invented rows remained.
- Judge: `accept`, citing `mimic-fhir/sql/fhir_medication_request.sql:43-44,172-177` and the unavailable FHIR validity-period paths. Implied exact tuple fidelity: 691,886/735,462 (94.075%).
- Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the judge.
- Artifacts: ViewDefinitions, `concept.sql`, `shape.demo.json`, `candidate.demo.parquet/`, `submit.slurm`, `hpc_job.json`, `comparison.full.json`, `run_meta.full.json`, and stage evidence in this attempt directory.
- Shared notes: updated the existing prescription medication identifier entry and the existing invalid-validity-period and datetime transformation entries; added the dataset-wide “Prescription route and Medication code displays are null” entry. No carryover stages were invalidated.
