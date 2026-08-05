---
name: pathling-sql
description: Provision FHIR ViewDefinitions and sql-view Libraries on Pathling and execute derived SQL via $sqlquery-run — the proven pattern from orchestration-new/scripts/sofa_provisioning. Register ViewDefinition via PUT, register Library with relatedArtifact labels, execute through Pathling client's sqlquery_run_sync(). Trigger phrases include "provision view", "register ViewDefinition", "pathling SQL", "sqlquery-run".
---

# pathling-sql

Registering FHIR ViewDefinitions, registering sql-view Libraries with
`relatedArtifact` labels referencing the ViewDefinition, and executing
derived SQL through Pathling's `$sqlquery-run` endpoint.

The canonical provisioning flow is demonstrated in
`../master_thesis_pipeline/orchestration-new/scripts/sofa_provisioning/register_patient_sofa.py`.
This is the **only** approved pattern — there is no `$aggregate` or `$sql`
flow for concept ports.

## Proven provisioning flow

### 1. Register ViewDefinition

```python
client.put_definitional(
    resource_type="ViewDefinition",
    resource_id="<vd-id>",
    resource_body=viewdefinition_dict,
)
```

The ViewDefinition JSON uses the `select[].column[].{path, name}` format
with optional `forEach`/`forEachOrNull` — see `fhir-mapping` skill for the
exact structure.

### 2. Register sql-view Library

```python
import base64

sql_bytes = sql_text.encode("utf-8")
encoded = base64.b64encode(sql_bytes).decode("ascii")

library_body = {
    "resourceType": "Library",
    "status": "active",
    "url": "<library_url>",
    "type": {
        "coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/library-type",
            "code": "sql-view"
        }]
    },
    "content": [{
        "contentType": "application/sql",
        "data": encoded
    }],
    "relatedArtifact": [{
        "type": "depends-on",
        "label": "<view_definition_label>",
        "resource": "<view_definition_url>"
    }]
}

client.put_definitional(
    resource_type="Library",
    resource_id="<library-id>",
    resource_body=library_body,
)
```

### 3. Execute SQL

```python
vd_dep = [{"label": "<vd_label>", "resource": "<vd_url>"}]
lib_dep = [{"label": "<lib_label>", "resource": "<lib_url>"}]

columns, rows = client.sqlquery_run_sync("SELECT count(*) AS n FROM <lib_label>", lib_dep)
```

The Pathling client adapter lives in
`../master_thesis_pipeline/orchestration-new/src/services/pathling_client.py`.

## SQL authoring patterns

### Polymorphic field coalescing

When a ViewDefinition extracts multiple variants of a polymorphic field,
the derived SQL must COALESCE them:

```sql
SELECT
    encounter_id,
    COALESCE(effective_datetime, effective_period_start) AS charttime,
    value AS valuenum,
    unit AS valueuom
FROM v_concept
```

### JOIN patterns

Concepts that reference multiple FHIR resources require JOINs:

```sql
SELECT o.patient_id, o.encounter_id, e.period_start
FROM v_observation_concept o
LEFT JOIN v_encounter_concept e ON o.encounter_id = e.encounter_id
```

### ICU stay filtering

Join against the ICU-stay Encounter view:

```sql
SELECT v.*
FROM v_vitalsign v
INNER JOIN v_icustay_detail d ON v.encounter_id = d.encounter_id
```

### Itemid / code filtering

```sql
WHERE system = '<source coding system>'
  AND code IN ('220045', '220050', '220052')
```

### Value constraints

```sql
WHERE
    value IS NOT NULL
    AND CAST(value AS DOUBLE) > 0
    AND TRY_TO_TIMESTAMP(effective_datetime) IS NOT NULL
```

### Spark SQL dialect notes

- `TRY_TO_TIMESTAMP(col)` for nullable FHIR datetime parsing (from
  `MIMIC_NOTES.md` — safer than `to_timestamp`, which throws on null/malformed).
- `CAST(value AS DOUBLE)` for FHIR Quantity values.
- `DATE_TRUNC('DAY', ts)` for day-level bucketing.
- Check `../master_thesis_pipeline/paper_reproductions/MIMIC_NOTES.md` for
  dataset-specific quirks (datetime parsing, code system flatness, etc.).

## Output requirements

The final `concept.sql` must be self-contained within the sql-view Library
— it references the registered ViewDefinition but must produce the output
table shape matching the original concept exactly (same column names, types,
row count).

## Pathling configuration

The Pathling server config lives in
`../master_thesis_pipeline/orchestration-new/config/pathling_config.yaml`:

```yaml
active_environment: dev
environments:
  dev:
    base_url: http://localhost:8080/fhir/
  prod:
    base_url: https://pathling.dw.csiro.au/fhir/
    # ... OAuth config ...
```

The default dev environment targets a local Docker Pathling container.
