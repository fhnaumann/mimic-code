Concept `suspicion_of_infection`, attempt `0001`; hpc-poller evidence.

Slurm job `30310841` completed successfully after two polls; accounting state was `COMPLETED`, elapsed 194 seconds, with no fatal markers. `run_meta.full.json` recorded 190.19 seconds execution and 1.648 seconds comparison.

Comparator verdict: `review`, tier `contested`; this is a semantic review, not a crash or mechanical mismatch. Oracle and candidate row counts were both 735,462. The keyed comparison had 462,482 identical rows (62.88%), zero `only_oracle`, zero `only_candidate`, 269,997 `differing_conflict`, and 2,983 `differing_null_only`. Conflicting columns included `antibiotic_time` (210,189), `antibiotic` (205,135), `suspected_infection_time` (112,205), `culture_time` (106,644), `hadm_id` (83,662), `specimen` (73,838), `suspected_infection` (70,481), `positive_culture` (44,420), and `stay_id` (18,333). Candidate-null columns included culture/positivity/specimen/suspected time (53,450 each), antibiotic_time (45,436), and stay_id (27,411).

The comparator attempted upstream DST attribution but explained only 54 of 269,997 conflicts; 269,943 remained unexplained. It reported `judge_required: true` and `diagnostician_required: true`, so the mismatch-diagnostician must diagnose before a judge is convened. The schema was compatible and no unrepresentable declaration was present.

Fetched artifacts: `comparison.full.json`, `run_meta.full.json`, and `hpc_accounting.json` in `mimic-iv/concepts_fhir/concepts/sepsis/suspicion_of_infection/attempt_0001/`; `hpc_job.json` records job `30310841`.
