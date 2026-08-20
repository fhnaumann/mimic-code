# Mismatch-diagnostician evidence

The full result is a `review` at the `contested` tier, not a mechanical
mismatch. The comparator attributed 67 of 70 conflicts to its exhaustive
America/New_York DST replay; diagnosis focused on the three residual rows.

The three are unkeyed duplicate-group alignment artifacts. Request-level
re-pairing in the prior full-data evidence re-pairs them to additional
DST-normalized endpoints; attempt 0003 is semantically identical for all
compared columns and reproduces the same 70/67/3 counts. This is upstream ETL
transformation loss, not a candidate SQL/ViewDefinition bug.

The citation is `mimic-fhir/sql/fhir_medication_request.sql:43-44`, which casts
coalesced prescription endpoints through `TIMESTAMPTZ`, and
`:172-177`, which writes only the transformed complete, non-reversed period.
The cast maps a nonexistent New York spring-forward 02:xx wall time to 03:xx;
the original is not retained. `authoredOn` at `:55,124` is pharmacy `entertime`,
not either endpoint, and identifiers/references at `:111-124` carry identity
only. No FHIR query can recover the relational endpoint.

The separate 43,453 `differing_null_only` rows are the same ETL's omitted
invalid/incomplete periods and consequent unavailable ICU assignment:
candidate NULL counts are starttime 43,369, stoptime 43,422, and stay_id
13,494. No carryover stage is blamed and no retry is recommended. The
diagnosis found no new dataset-wide quirk; both endpoint loss and DST behavior
are already recorded in `MIMIC_NOTES.md`.

Evidence read: `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, canonical antibiotic SQL,
both antibiotic carryovers, attempt 0003 SQL/ViewDefinitions and comparison,
prior antibiotic evidence, and the cited upstream medication-request and
related ETL files. No files were edited and no commit was made.
