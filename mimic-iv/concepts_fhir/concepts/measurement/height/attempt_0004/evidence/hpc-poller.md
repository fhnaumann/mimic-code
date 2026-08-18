# HPC-poller evidence

Job `30109480` completed normally and the full comparison artifacts were
fetched. The comparator returned `review`, tier `attributed`, with
`judge_required: true` and `diagnostician_required: false`. The candidate and
oracle each have 33,474 rows and matching schema. Keyed diff on `stay_id`:
33,472 identical rows and 2 `differing_conflict` rows on `charttime`; all 2
were replayed to the upstream TIMESTAMPTZ DST shift with zero residual. There
were no only-oracle, only-candidate, or differing-null-only rows. Row count was
reported, not gated.

The artifact cites `mimic-fhir/sql/fhir_observation_chartevents.sql:9,67`
among the upstream transformation sites and requires the judge to confirm
that provenance applies to this charttime column and that 2/33,474 is
consistent with DST-gap rarity. Slurm accounting reported 122 seconds elapsed.

Artifacts:

- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/comparison.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/run_meta.full.json`
- `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0004/hpc_accounting.json`
