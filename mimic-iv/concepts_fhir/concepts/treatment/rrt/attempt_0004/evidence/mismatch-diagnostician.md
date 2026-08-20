## Diagnosis — concept `rrt`, attempt 0004

**Root cause:** attempt 0004 is semantically correct for the served FHIR data. All 449 oracle-only and 241 candidate-only multiset entries are second-order consequences of irreversible upstream DST-gap normalization, not a port bug or coverage gap.

### Full-oracle replay

The PostgreSQL `TIMESTAMPTZ` behavior was replayed as an `America/New_York` wall-time round trip; the canary transformed `2141-03-12 02:10:00` to `03:10:00`.

| Stream | Selected rows | Shifted source rows |
|---|---:|---:|
| `chartevents` | 4,004,998 | 608 chart times |
| `inputevents` | 85,372 | 27 intervals: 13 starts and 14 ends |
| `procedureevents` | 14,003 | 0 |
| **Total** | **4,104,373** | **635** |

Additional checks found zero selected input rows with `rate IS NULL`, zero selected procedure rows excluded by `value IS NULL`, and zero shifted selected procedure endpoints.

The raw-timestamp source replay produced 2,827,715 rows with zero differences against `mimiciv_derived.rrt`. The ETL-normalized replay produced 2,827,507 rows with 449 oracle-only and 241 shifted-replay-only rows, and matched attempt 0004 exactly after projecting the five manifest columns. Thus the residual after replay is zero in both classes.

### Propagation and citations

- `mimic-fhir/sql/fhir_observation_chartevents.sql:9` casts `charttime` to `TIMESTAMPTZ`; `:67` writes the normalized value to `Observation.effectiveDateTime`.
- `mimic-fhir/sql/fhir_medication_administration_icu.sql:8-9` casts input start/end times; `:61-69` writes the normalized endpoints.
- `mimic-fhir/sql/fhir_procedure_icu.sql:10-11,73-75` applies the analogous transformation, but zero selected RRT procedure endpoints shifted.
- `mimic-iv/concepts/treatment/rrt.sql:260,296-313` uses `UNION DISTINCT`; `:316-326` uses the inclusive `LEFT JOIN ... BETWEEN` overlay. These propagate one moved source timestamp into the 449/241 multiset divergence through collisions, interval partners, multiplicity, and `COALESCE` values.

The comparator correctly reports `unavailable_no_key`, so 449 and 241 cannot align individual rows; the source-side replay closes the full multisets exactly and is weaker than keyed attribution. Code `225965` is present in the current port, and no selected input interval loses its start through the ETL rate branch; no selected procedure row relies on an omitted value discriminator. The added resource keys are equality/provenance outputs only. Resource IDs were not parsed or regenerated.

**Classification:** upstream transformation loss; no SQL/ViewDefinition fix and no carryover invalidation. The original 02:xx wall times are absent from semantic FHIR elements and cannot be recovered by any permitted query.

**Recommendation:** accept the documented divergence under the DST-defect exemption, explicitly recording the weaker unkeyed alignment and exact source-side multiset closure.

No new dataset-wide fact was established and no fragment was appended. No HPC job or state transition was performed by the diagnostician.
