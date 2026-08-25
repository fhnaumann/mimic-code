# Source-analyst evidence — lods attempt_0001

The source analyst read `mimic-iv/concepts/score/lods.sql`, the `lods` DAG node,
`MIMIC_NOTES.md`, all available `MIMIC_NOTES.d` fragments, and the six
dependency SQL sources. It checked the DAG SHA256, source tables and columns,
filters, joins, time windows, literal codes, CASE thresholds, output types,
grain, dependency columns, and representability risks.

The canonical query produces one row per ICU `stay_id` with ten outputs:
`subject_id`, `hadm_id`, `stay_id`, `lods`, and six nullable component scores.
It consumes the completed `bg`, `first_day_gcs`, `first_day_lab`,
`first_day_urine_output`, `first_day_vitalsign`, and `ventilation` dependency
views. Direct filters are chartevents item `226732`, CPAP/BiPAP text patterns,
and ventilation status `InvasiveVent`; CPAP and blood-gas interval boundaries
and component NULL semantics are clinically consequential.

Carryover was written to
`mimic-iv/concepts_fhir/carryover/lods/source-analyst.md` and recorded with
`mimic_utils carryover-record`. No dataset-wide quirk was discovered and no
`MIMIC_NOTES.d/lods.md` fragment was created at this stage.
