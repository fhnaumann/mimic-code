Evidence block

The FHIR prober read the source carryover, curated notes, all current notes
fragments, the completed `weight_durations` attempt, local embedded Pathling
data, DuckDB demo oracle data, and the relevant MIMIC-on-FHIR ETL SQL. It
confirmed ICU Encounter and Patient identifier/resource-key mappings, the ICU
chartevents coding system with exact codes 226512 (admit) and 224639 (daily),
numeric Quantity value and unit paths, and the required opaque equality joins.
The demo projection retained 570/570 target observations and matched source
keys/times and numeric values within tolerance. The completed dependency is
consumed from its published boundary and must be joined by its opaque
`icu_encounter_key`, not by an unavailable `stay_id` or parsed resource id.

The prober confirmed that FHIR datetime aliases require direct
`TIMESTAMP_NTZ` casts before arithmetic/COALESCE. It also verified that the
dependency's ICU Encounter `intime` lineage can inherit upstream DST-gap
normalization, with nine related effects already reported by the dependency;
the original wall time is not recoverable by allowed queries. Demo data did not
exercise the gap. Global chartevents omission predicates were also checked and
were unexercised for these weight items.

Reusable mapping was written to
`mimic-iv/concepts_fhir/carryover/first_day_weight/fhir-prober.md` and recorded
with the carryover ledger. The prober appended two dataset-level findings to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/first_day_weight.md`; `MIMIC_NOTES.md`
was not edited. No commit was made.
