Evidence block — chemistry attempt_0003

Slurm job `29679671` completed normally after two polls; no crash markers, and fresh full artifacts were fetched. Comparator verdict: `review`, tier `contested`; this is a legitimate verdict, not a failure.

Schema matched exactly with no missing, extra, or incompatible columns. Candidate and oracle each contained 3,811,523 rows, with row count reported but not gated. Divergence was exactly 198 `differing_conflict` rows (0.005%), all on `charttime`; there were no `only_oracle`, `only_candidate`, `differing_null_only`, or unresolvable rows. Identical rows: 3,811,325 (99.9948%). Samples consistently showed a +1 hour candidate shift, e.g. candidate `2144-03-08T03:15:00` vs oracle `02:15:00`, matching the known DST-gap transformation signature.

Artifacts:
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/chemistry/attempt_0003/run_meta.full.json`

The review requires diagnosis and an upstream ETL citation before the equivalence judge. No implementation or notes files were modified by polling.
