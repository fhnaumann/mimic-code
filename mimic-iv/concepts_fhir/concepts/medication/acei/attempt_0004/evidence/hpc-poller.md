Evidence block — concept `acei`, stage `hpc-poller`, attempt 0004.

Slurm job `29599959` completed normally and the fresh full comparison was
fetched. The embedded Pathling/Spark run did not crash, time out, or encounter
fatal markers. Oracle and candidate row counts both equal 112,014 (reported,
not a hard gate), and the schema matched exactly:
`subject_id`, `hadm_id`, `acei`, `starttime`, `stoptime` with compatible
integer/string/timestamp_ntz types.

The full verdict is `review`, exit code 2, comparison mode
`full_tuple_multiset`, classification `unavailable_no_key`, tier `contested`.
The corrected port now has equal row count, but the unkeyed diff reports 9,073
only-candidate and 9,073 only-oracle tuples; the comparator cannot distinguish
NULL-for-value/transformed tuples from invented rows without a natural key.
No schema mismatch or declared-unrepresentable blocker was reported.

Fetched artifacts:

- `comparison.full.json`
- `run_meta.full.json`

The result is judge-required. The prior diagnostician supplied the required
ETL citations for validity-period omission and DST normalization; no judge
verdict is inferred here.
