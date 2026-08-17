# Mismatch-diagnostician evidence

The diagnostician inspected the current attempt 0002 comparison and confirmed that the prior attempt's diagnosis remains applicable after the required opaque key projection. This is upstream ETL transformation loss, not a fixable port bug.

The upstream statement `mimic-fhir/sql/fhir_observation_labevents.sql:15` casts source `labevents.charttime` through `TIMESTAMPTZ`, and line 121 writes the transformed value to `Observation.effectiveDateTime`. The comparator directly attributed 138 of 154 conflicts. The remaining 16 are downstream effects through the canonical and candidate strict prior windows (`kdigo_creatinine.sql:27-30,42-45`; attempt 0002 `concept.sql:57-60,68-71`): seven also have shifted current charttime and nine retain current charttime while a shifted prior observation changes ordering or 48-hour/7-day boundary membership. The parallel specimen path also applies the cast at `mimic-fhir/sql/fhir_specimen_lab.sql:9,18,58`.

FHIR retains only the normalized effective time and labevent provenance; a normalized 03:xx is indistinguishable from a genuine 03:xx. Exact source chronology and window membership are unrecoverable by any FHIR query. The required key additions are opaque identity outputs and are excluded from value comparison; they do not alter the six value expressions. No carryover stage should be invalidated and no new attempt is required. No implementation artifacts were changed.

The provisional `MIMIC_NOTES.d/kdigo_creatinine.md` lead was checked against the current comparison and ETL source. The diagnostician appended the current reconfirmation to that fragment.
