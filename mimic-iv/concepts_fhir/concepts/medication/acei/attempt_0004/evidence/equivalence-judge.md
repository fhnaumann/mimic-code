Evidence block — concept `acei`, stage `equivalence-judge`, attempt 0004.

Verdict: `accept`, tier `contested`, classification
`unavailable_no_key`. Divergent dependencies: none; acei is level 0.

The full schema and row count match exactly at 112,014 rows. The unkeyed
comparison reports paired 9,073 only-candidate and 9,073 only-oracle tuples
(8.0999%); the evidence accounts for the substitutions as 9,059 NULL/NULL
tuples from 9,050 invalid plus 9 incomplete source intervals and 14
DST-normalized endpoint tuples. With no natural key, the comparator cannot
separate these from invented rows, but the exact numerical account, samples,
and attempt history support transformed counterparts rather than fan-out.

The contested accept is supported by the upstream ETL citations:
`mimic-fhir/sql/fhir_medication_request.sql:172-177` emits
`dispenseRequest.validityPeriod.start/end` only for valid complete intervals;
otherwise the endpoints are absent. `authoredOn` at line 124 comes from
pharmacy `entertime` at line 55 and cannot recover either endpoint.
`fhir_medication_request.sql:43-44` casts through `TIMESTAMPTZ`, irreversibly
normalizing DST-gap 02:00 wall times to 03:00. No FHIR query can invert either
loss. All defensible direct and ingredient mappings were tried; the prior
186-row medication-mix omission was fixed in attempt_0004 with
`ingredient.itemReference` and `UNION ALL`.

Fidelity figures: `identical_fraction` and `representable_fraction` are not
emitted for this unkeyed multiset result; descriptive exact multiset overlap is
102,941/112,014 (91.9001%). The cited divergence is intrinsic to the served
FHIR representation, not a remaining port bug. No MIMIC_NOTES.md change was
requested by the judge.

Recommended controller action: `uv run mimic_utils accept-divergence acei`
with the judge's cited justification. No files were modified by the judge.
