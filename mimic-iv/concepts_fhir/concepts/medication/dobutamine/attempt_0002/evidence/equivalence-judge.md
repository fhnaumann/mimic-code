# Equivalence judge evidence

Concept: `dobutamine`  
Attempt: `0002`  
Verdict: `accept`  
Tier: `contested`

The judge read the loop contract, curated `MIMIC_NOTES.md`, the attempt
comparison and implementation artifacts, attempt history, canonical SQL,
diagnostician evidence, and the upstream
`mimic-fhir/sql/fhir_medication_administration_icu.sql`.

The judge accepted the divergence. `MedicationAdministration.identifier.value`
does not carry `inputevents.linkorderid`; the ICU ETL writes no input-event
identifier, so the declared typed NULL is the faithful representation. The
remaining key substitution and endtime conflict are intrinsic upstream loss:
lines 8-9 cast source endpoints through `TIMESTAMPTZ`, lines 61-65 write only
the transformed values to `effectivePeriod`, and line 20 constructs an opaque
timestamp-free UUID. The source 2165-03-10 02:28 wall time is therefore
irreversibly normalized to 03:28 in the DST spring-forward gap and cannot be
recovered by a FHIR query. The affected conflict is 1/8,513 (0.0117%),
consistent with DST-gap rarity.

Fidelity is 0/8,513 overall because of the declared absent column, and
8,511/8,513 (99.9765%) over representable columns. No artifacts were changed
by the judge and no new notes finding was identified.
