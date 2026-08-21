# Source analyst evidence

Evidence block — Concept: `vasoactive_agent`. Read canonical SQL at `mimic-iv/concepts/medication/vasoactive_agent.sql`, all seven dependency SQL files, DAG, `LOOP_CONTRACT.md`, `MIMIC_NOTES.md`, relevant medication fragments, and `MIMIC_NOTES.d/README.md`. Verified the canonical SQL SHA against the DAG.

Found seven `mimiciv_derived` dependencies; underlying source table `mimiciv_icu.inputevents`; columns including `stay_id`, `starttime`, `endtime`, `vaso_rate`, `itemid`, `rate`, `amount`, `rateuom`, `patientweight`, and `linkorderid`. Recorded exact itemids `221653`, `221662`, `221289`, `221906`, `221749`, `222315`, `221986`, unit discriminators, the final `endtime IS NOT NULL` filter, seven `LEFT JOIN`s, `UNION DISTINCT`, and `LEAD` windowing. No coding-system URI, ICD, or LOINC codes appear in the SQL.

Reusable analysis written to `mimic-iv/concepts_fhir/carryover/vasoactive_agent/source-analyst.md`; carryover recorded successfully with `mimic_utils carryover-record`. No FHIR port authored and no commit made.

Summary: the concept constructs consecutive per-`stay_id` medication-boundary intervals and overlays seven dependency-derived vasoactive rates.
