Evidence block — HPC poller for `height`, attempt `0001`.

Polled job `29715902`; outcome was `complete` with Slurm state `COMPLETED` and elapsed 138 seconds. The full comparator executed and produced `review`, not a crash: schema identity matched, row count was 33,474 candidate versus 33,474 oracle (reported, not gated), 33,470 rows were identical, and 4 rows had `differing_conflict` on `charttime` (0.012%). The tier is `contested`; `judge_required` is true. Samples show candidate timestamps exactly one hour after oracle timestamps while identifiers and height agree.

Artifacts fetched: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` under `mimic-iv/concepts_fhir/concepts/measurement/height/attempt_0001/`. A contested diagnosis is required before convening the judge under the loop contract.
