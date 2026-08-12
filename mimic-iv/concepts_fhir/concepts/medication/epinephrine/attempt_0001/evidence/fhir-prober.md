# FHIR-prober evidence

The prober read the curated `MIMIC_NOTES.md`, all existing provisional
`MIMIC_NOTES.d` fragments, and the reusable source analysis, then probed the
authoritative demo Delta with embedded Pathling 9.6.0/Spark 4.0.2 and checked
the read-only DuckDB demo oracle. It inspected the ICU MedicationAdministration
and Encounter profiles and the upstream ETL SQL.

The exact mapping is ICU `MedicationAdministration`, filtered by
`medication.ofType(CodeableConcept).coding` with system
`http://mimic.mit.edu/fhir/mimic/CodeSystem/mimic-medication-icu` and code
`221289`. The probe found 36 target resources/codings and one coding per
resource. `stay_id` is recovered by joining
`context.getReferenceKey(Encounter)` to the Encounter identifier system
`http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`, then casting its
string value to INTEGER. `rate` and `amount` map to dosage rate/dose Quantity
values and require FLOAT casts. `starttime` and `endtime` map to Period start
and end; both effective[x] variants were projected, with dateTime used as the
general end-time fallback. Datetime strings require TIMESTAMP_NTZ semantics.

`linkorderid` has no FHIR representation: ICU MedicationAdministration has no
identifier carrying it, so the implementation must emit typed NULL INTEGER.
Served Quantity values are decimal scale six; target values agreed within
1e-6. The full manifest key is `(linkorderid, starttime)` and has 24,470 rows.

Dataset-wide findings were appended by the prober to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/epinephrine.md`: no inputevent identifier
or linkorderid, effective[x] Period/dateTime branching, six-decimal ICU
MedicationAdministration quantities, one medication coding per resource, and
absence of CodeSystem resources in the authoritative Delta. The reusable
mapping is `mimic-iv/concepts_fhir/carryover/epinephrine/fhir-prober.md` and
was recorded with `mimic_utils carryover-record`.
