-- Does a *representable* unique key exist for the concepts whose manifest key
-- landed on an unmappable inputevents order identifier?
--
-- `oracle_manifest.py` searches size-first through a fixed identity/time
-- vocabulary, so a one-column unmappable key wins before any two-column
-- mappable key is considered, and the search stops at the first success. The
-- manifest therefore cannot tell you whether a representable key exists -- only
-- that one particular candidate was reached first. This settles it directly.
--
-- Run against the full oracle, e.g.
--   duckdb /scratch3/nau025/oracle/mimic4-full.db < probe_representable_keys.sql
--
-- Read the result as: if k_stay_start (or k_sse) equals n, that column set is a
-- unique key made only of columns MIMIC-on-FHIR carries. The missing orderid /
-- linkorderid is then demonstrably surplus to row identity, and the divergence
-- is ancillary in the sense LOOP_CONTRACT.md requires for an accept.

SELECT 'neuroblock'     AS concept,
       count(*)                                      AS n,
       count(DISTINCT (stay_id, starttime))          AS k_stay_start,
       count(DISTINCT (stay_id, starttime, endtime)) AS k_sse
FROM mimiciv_derived.neuroblock

UNION ALL
-- key_probes 6: (stay_id, starttime) was tried at full scale and FAILED, so
-- k_stay_start < n is expected here. k_sse is the open question -- it is the
-- only remaining representable candidate and was never probed.
SELECT 'epinephrine',
       count(*),
       count(DISTINCT (stay_id, starttime)),
       count(DISTINCT (stay_id, starttime, endtime))
FROM mimiciv_derived.epinephrine

UNION ALL
SELECT 'norepinephrine',
       count(*),
       count(DISTINCT (stay_id, starttime)),
       count(DISTINCT (stay_id, starttime, endtime))
FROM mimiciv_derived.norepinephrine

UNION ALL
-- key_probes 11: exhausted every candidate, including three-column ones, and
-- found nothing unique. Included as the control -- expect k < n on both.
SELECT 'phenylephrine',
       count(*),
       count(DISTINCT (stay_id, starttime)),
       count(DISTINCT (stay_id, starttime, endtime))
FROM mimiciv_derived.phenylephrine

UNION ALL
-- Accepted siblings, keyed on (stay_id, starttime) at key_probes 4. Expect
-- k_stay_start = n. They are the baseline the others are being judged against.
SELECT 'dopamine',
       count(*),
       count(DISTINCT (stay_id, starttime)),
       count(DISTINCT (stay_id, starttime, endtime))
FROM mimiciv_derived.dopamine

UNION ALL
SELECT 'dobutamine',
       count(*),
       count(DISTINCT (stay_id, starttime)),
       count(DISTINCT (stay_id, starttime, endtime))
FROM mimiciv_derived.dobutamine

ORDER BY concept;
