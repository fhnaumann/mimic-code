## ICU Encounter period endpoints are direct dateTime fields and are populated on the ICU stream
- Affected: `Encounter.period.start` and `Encounter.period.end` for `identifier.system = http://mimic.mit.edu/fhir/mimic/identifier/encounter-icu`
- Verified: `sofa` attempt_0001 embedded Pathling/Spark probe over the authoritative rebuilt Delta found 140/140 ICU Encounters with both `period.start` and `period.end` (637/637 across all Encounter streams); direct `TIMESTAMP_NTZ` casts agreed with `mimiciv_icu.icustays.intime/outtime` on 140/140 rows.

## ICU MedicationAdministration references its Encounter through `context`, not `encounter`
- Affected: `MedicationAdministration.context` and the ICU administration Encounter join
- Verified: `sofa` attempt_0001 embedded Pathling/Spark probe found the served schema field `context` and `context.getReferenceKey(Encounter)` populated on all 1,055 rows for codes `221653`, `221662`, `221289`, and `221906`; the corresponding `encounter.getReferenceKey(Encounter)` projection is not the served R4 field and failed on the unfiltered hospital stream.
