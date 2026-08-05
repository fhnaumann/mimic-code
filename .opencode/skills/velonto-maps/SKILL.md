---
name: velonto-maps
description: Resolve MIMIC coding systems and codes against Velonto FHIR ConceptMaps at https://velonto.dw.csiro.au/fhir via $translate, $expand, and VCL implicit ValueSets. Accept every actual ConceptMap relationship except explicit unmatched — a missing target remains unresolved. Preflight with full SHA256 of the FHIR JSON content. Snapshot ConceptMaps and ValueSets locally for reproducibility. Trigger phrases include "resolve code", "translate code", "Velonto", "ConceptMap", "terminology mapping".
---

# velonto-maps

Terminology resolution via Velonto FHIR ConceptMaps at
`https://velonto.dw.csiro.au/fhir`. This skill is authoritative for all
terminology operations in concept ports.

## Terminology policy (from AGENTS.md)

1. **Velonto FHIR ConceptMaps are authoritative.** All resolution starts
   and ends at `https://velonto.dw.csiro.au/fhir`.
2. **Source coding system + code first.** Identify the MIMIC source coding
   system before consulting any mapping.
3. **Accept every actual ConceptMap relationship except explicit `unmatched`.**
   A ConceptMap entry with `equivalence: unmatched` is the only refusal.
   A missing target (no ConceptMap entry at all for that source code)
   remains **unresolved** — it is not the same as unmatched.
4. **Explicit canonical for production `translate()`.** Every `$translate`
   in a ViewDefinition cites the exact ConceptMap canonical URL. Version is
   **separately** preflight-asserted — `url|version` is not a valid
   `$translate` parameter; the server resolves by URL alone.
5. **Preflight scope / version / content hash.** Before production use,
   fetch the ConceptMap, record `version` + `date`, and compute an SHA256
   of the **complete FHIR JSON content**.
6. **Local FHIR JSON snapshots.** Snapshot every ConceptMap and ValueSet
   used into the concept's port directory as `.fhir.json` files. These are
   ground truth for reruns.

## Velonto server

- Base URL: `https://velonto.dw.csiro.au/fhir` (note the `/fhir` suffix)
- No authentication required for dev
- MIMIC-on-FHIR IG loaded with:
  1. Stricter bindings of fields to ValueSets
  2. `Condition.code` binding replaced with a proper ICD-9/10 ValueSet
     with full hierarchy support
- Config reference: `../master_thesis_pipeline/orchestration-new/config/terminology_config.yaml`

## Coding system discovery

Read the complete stored `Coding` from the populated FHIR data before map
selection. Never infer a local MIMIC system URI from a table name or numeric
item ID. Record `system`, `version`, `code`, and `display` when present, then
verify that the chosen ConceptMap group has the expected source system and
translation direction.

## Operations

### $translate — single code mapping

```
GET https://velonto.dw.csiro.au/fhir/ConceptMap/$translate
    ?url=<percent-encoded ConceptMap canonical URL>
    &code=<code>
    &system=<sourceSystem>
```

Bare `$translate` without `url` may be used to discover candidate maps. For
production, cite the explicit ConceptMap canonical URL in the ViewDefinition.
The version number is preflight-asserted out-of-band — never append it to the
canonical passed to Pathling `translate()`.

### $expand — code set expansion

For hierarchy-constrained code sets (e.g. all ICD-10 descendants of `K85`),
use VCL implicit ValueSets:

```
GET https://velonto.dw.csiro.au/fhir/ValueSet/$expand
    ?url=http://fhir.org/VCL?v1=<percent-encoded VCL expression>
```

VCL syntax (see the `/vcl` skill in paper_reproductions):
- `<<` — self and all descendants
- `(http://hl7.org/fhir/sid/icd-10-cm)concept<<"K85"` — all codes under K85

### $lookup — code display name

```
GET https://velonto.dw.csiro.au/fhir/CodeSystem/$lookup
    ?code=<code>
    &system=<system>
```

### ConceptMap search

Search for relevant ConceptMaps:

```
GET https://velonto.dw.csiro.au/fhir/ConceptMap
    ?source-uri=<sourceSystem>
    &target-uri=<targetSystem>
```

## Preflight hash procedure

```bash
# Fetch ConceptMap
curl -s "https://velonto.dw.csiro.au/fhir/ConceptMap/<id>" \
  -H "Accept: application/fhir+json" \
  -o cm_snapshot.fhir.json

# Extract version and date
jq '{version: .version, date: .date}' cm_snapshot.fhir.json

# Compute SHA256 of the complete FHIR JSON content
sha256sum cm_snapshot.fhir.json | cut -d' ' -f1
```

Record the hash in the concept's port directory as `terminology_hashes.json`.
Do the same for every ValueSet snapshot.

## Equivalence handling

Only `equivalence: unmatched` is a refusal condition. All other values
(`equal`, `equivalent`, `wider`, `narrower`, `inexact`, `subsumes`,
`specializes`) are accepted.

For codes with no ConceptMap entry at all, report them as **unresolved**
(not unmatched). These are candidates for representability exceptions
but may be resolvable through alternative mapping paths.
