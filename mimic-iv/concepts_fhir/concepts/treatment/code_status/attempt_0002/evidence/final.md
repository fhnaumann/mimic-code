# Final evidence — code_status

Concept: `code_status`

Terminal state: `COMPLETED_WITH_DIVERGENCE`, accepted by the equivalence judge
after full-data run 2. Full-data runs consumed: **2 of 10**.

Final verdict: `review`, tier `gap_shaped`, classification
`unavailable_no_key`. Schema identity passed. Oracle rows: 269,072. Candidate
rows: 71,141. Divergence: 197,931 `only_oracle`, zero `only_candidate`, and no
remaining value conflicts. The judge accepted that these rows are the absent
hospital General Care / Code status POE-detail branch: no served FHIR resource
or path carries the POE event, `poe_detail.field_value`, or `poe.ordertime`.
The nearest MedicationRequest POE mapping was tested and rejected as an
unrelated medication/IV/TPN stream. The representable chart branch was exact
after UUID-witnessed correction of the nine DST-normalized timestamps from
attempt 0001: diagnostic fidelity 71,141/71,141 (100%). Overall oracle
coverage was 71,141/269,072 (26.44%). Formal identical/representable fractions
were unavailable because the concept has no key and residual pairing did not
apply.

Controller command completed:
`uv run mimic_utils accept-divergence code_status --justification "..."`

Primary artifacts:
- `mimic-iv/concepts_fhir/concepts/treatment/code_status/attempt_0002/`
- `comparison.full.json`
- `run_meta.full.json`
- `concept.sql`
- four `ViewDefinition.*.json` files

Append-only dataset fragment entries added to
`mimic-iv/concepts_fhir/MIMIC_NOTES.d/code_status.md`:
1. Chartevents FHIR ETL drops one hard-coded duplicate row.
2. Chartevents FHIR ETL omits rows whose source value is NULL.
3. Chartevents effectiveDateTime irreversibly normalizes DST-gap charttime.
4. Chartevents Observation.id preserves the pre-normalization charttime input.
5. Hospital General Care code-status POE events are absent from served FHIR.

`MIMIC_NOTES.md` was not edited. No git operations were performed.
