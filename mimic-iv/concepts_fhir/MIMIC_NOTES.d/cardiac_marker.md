## Filter itemid-derived Observation codes as strings before integer casts
- Affected: `Observation.code.coding.code` and any itemid-derived Observation filter
- Verified: `cardiac_marker` attempt_0001 embedded Delta probe; an unscoped `CAST(code AS INT)` failed on served Observation code `85354-9` (an ED LOINC), while filtering the confirmed `mimic-d-labitems` system plus exact string codes returned 51003=278, 50911=187, and 50963=76 rows. Cast only after the system/code filter, or use `TRY_CAST`.
