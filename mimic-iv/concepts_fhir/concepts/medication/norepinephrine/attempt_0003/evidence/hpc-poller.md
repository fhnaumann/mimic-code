# HPC poll evidence — norepinephrine attempt_0003

The controller polled only job `30235382` and fetched a complete full-data
verdict. Slurm elapsed time was 26 seconds. The comparator returned `review`,
tier `contested`, with both `diagnostician_required` and `judge_required` true.

The candidate executed with schema identity and 336,000 rows, equal to the
oracle. The diff reported 336,000 `only_oracle`, 336,000 `only_candidate`, and
zero aligned/identical rows. This is explicitly VOID DIFF because declared
the row counts are key-selection artifacts, not a fidelity measure. Key DST
attribution was attempted but incomplete, with zero attributed rows. Required
key columns `icu_encounter_key` and `patient_key` were present.

Fetched artifacts in this attempt: `comparison.full.json`, `run_meta.full.json`,
and `hpc_accounting.json`. The review must now receive a fresh diagnosis and
then the equivalence judge; it is not a match or a mechanical mismatch.
