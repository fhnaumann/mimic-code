## Current full warehouse age and admission-time mappings are exact after upstream fixes
- Affected: `Patient.birthDate`-derived admission age and `Encounter.period.start`
- Verified: `age` attempt 0004 full-data comparison — all 431,231 representable rows matched the oracle exactly for `age` and `admittime`; the prior attempt's 460 birthDate-derived age conflicts and 44 DST admission-time conflicts were not present in this current full warehouse/ETL snapshot. The separate `anchor_age` and `anchor_year` fields remain absent and were emitted as typed NULLs.
