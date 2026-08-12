# Evidence: mismatch-diagnostician

Concept `invasive_line`, attempt `0001`.

The diagnosis found no port bug and no carryover invalidation is warranted. The 657 `line_site` conflicts are intrinsic: `mimic-fhir/sql/fhir_procedure_icu.sql:12` trims and whitespace-normalizes `procedureevents.location`, and lines `62-69` serialize only the transformed body-site code. The full-data residual is exactly 555 `Right Antecube ` and 102 `L Ventricular ` source values whose trailing whitespace is lost, with no FHIR field retaining the original string. The seven `starttime` conflicts are the comparator-attributed DST-gap transformation, with Procedure-specific provenance at `mimic-fhir/sql/fhir_procedure_icu.sql:10,73-76`. The one `endtime` conflict overlaps a line-site row and is also a DST-gap rewrite from lines `11,73-76` (stay `38150916`, 02:30 to 03:30); the original wall time is not recoverable from FHIR.

Recommendation: do not retry; route this `contested` review to the equivalence judge. The diagnosis and citations are concept-specific and the Procedure trimming/DST findings were appended to `mimic-iv/concepts_fhir/MIMIC_NOTES.d/invasive_line.md`.
