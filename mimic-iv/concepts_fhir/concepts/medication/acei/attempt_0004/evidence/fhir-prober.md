Evidence block — concept `acei`, stage `fhir-prober`, attempt 0004.

Reran the invalidated probe after reading LOOP_CONTRACT.md, MIMIC_NOTES.md,
source carryover, invalidation reason, prior full comparison, and attempt_0003
evidence. The corrected mapping includes both direct MedicationRequest
references and medication-mix resources whose repeated
`Medication.ingredient.itemReference` components point to component
Medications. The mix branch must use `UNION ALL` and preserve component
multiplicity.

Authoritative demo Delta probe counts: 15,225 pharmacy-linked requests;
12,382 direct requests and 2,843 mix requests; 314 mix resources with 634/634
resolved ingredient references (310 two-component, 2 three-component, 2
four-component mixes); 5,705 expanded mix rows, matching source multiplicity.
All 631 distinct source drug strings and all 314 ingredient name multisets
matched exactly. The name identifier system is
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-name`; mix
resources use the medication-mix identifier. The ten ACEI predicates remain
the literal case-insensitive source predicates.

Patient and hospital Encounter identifier mappings, integer casts, and
TIMESTAMP_NTZ validity mappings remain unchanged. Invalid/incomplete validity
periods remain typed NULLs; `authoredOn` is not a substitute. The updated
concept analysis was written and recorded at
`mimic-iv/concepts_fhir/carryover/acei/fhir-prober.md` with its carryover
ledger. The existing MIMIC_NOTES.md prescription medication identifier entry
was sharpened with mix URI/multiplicity evidence; no new dataset-wide entry
was added. No immutable attempt artifact was modified.
