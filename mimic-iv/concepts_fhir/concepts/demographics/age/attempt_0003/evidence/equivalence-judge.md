# Evidence: equivalence-judge

The independent judge read the authoritative contract, canonical curated
MIMIC notes, current comparison and attempt artifacts, prior attempt evidence,
and the diagnostician's findings. It did not use provisional fragments. There
are no divergent dependencies.

## Verdict: accept

The review is `contested` with 504 conflicts: 460 `age` conflicts (0.107%)
and 44 `admittime` conflicts (0.010%). The 44 admission-time conflicts are
exhaustively replayed to the upstream DST cast. The remaining 460 age conflicts
are intrinsic upstream transformation loss: `mimic-fhir/sql/fhir_patient.sql:15`

The candidate's direct birthDate/year mapping is the best exact representable
typed NULL declarations for `anchor_age` and `anchor_year` are valid ancillary
gaps: all 431,231 rows and the `hadm_id` grain are preserved, with no
only-oracle or only-candidate rows. Representable fidelity is 430,727/431,231
(99.8831%); total identical rows are 0/431,231 because the declared columns
are always NULL. The judge accepted rather than blocked under the contract's
explicit Patient.birthDate and DST transformation-loss provisions.

Judge citation/justification for controller:

> Intrinsic upstream transformation divergence. `fhir_patient.sql:15,108`
> synthesizes `Patient.birthDate` from `MIN(transfers.intime)-anchor_age`, while
> canonical `age.sql:30` requires the unrecoverable `anchor_age`/`anchor_year`
> pair, explaining all 460 age conflicts. `fhir_encounter.sql:65,149-151`
> irreversibly normalizes 44 DST-gap admission times, exhaustively replayed by
> the comparator. The anchor outputs are valid ancillary typed NULLs; all rows,
> keys, and grain are preserved. Under the contract's explicit birthDate and
> DST upstream-defect exemptions, these conflicts are accepted rather than
> blocked, including their clinically meaningful effect on age.
