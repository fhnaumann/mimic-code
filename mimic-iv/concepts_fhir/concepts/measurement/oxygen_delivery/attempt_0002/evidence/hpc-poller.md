# Evidence: hpc-poller

Job `29938370` completed normally after two polls; Slurm elapsed time was 323 seconds. The full comparator returned `review`, not a crash or mismatch. Oracle rows: 601,546; candidate rows: 601,543; identical rows: 601,509 (99.9938%).

Routing: divergence tier `attributed`; `diagnostician_required=false`; `judge_required=true`.

Diff: 3 `differing_conflict`, 34 `only_oracle`, and 31 `only_candidate`. Every finding was replayed to the upstream `TIMESTAMPTZ` DST shift, with complete conflict and key attribution and zero residual. Three conflict rows were also attributed by key collision. No gap-shaped or unresolved residual remained. The artifact cites the relevant `mimic-fhir` cast sites and requires the judge to confirm element provenance, DST-gap rarity, and the aggregation result at collision keys; no resource-id recovery is permissible.

Artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in this attempt.
