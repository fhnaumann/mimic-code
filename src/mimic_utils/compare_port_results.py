"""Deterministic comparator for a MIMIC-on-FHIR concept port.

Two *different* queries must produce the *same table*: the canonical MIMIC-IV
SQL over relational MIMIC-IV, and an agent-authored FHIR ViewDefinition + SQL
over MIMIC-on-FHIR.  There is no shared query, so this comparison **is** the
experimental claim.  ``mimic-iv/concepts_fhir/LOOP_CONTRACT.md`` is
authoritative on gate semantics; this module implements them.

Two modes, deliberately different strengths:

``shape``
    The **demo** gate.  Cheap, local, seconds.  Checks only that the candidate
    executed and returned the right column names and compatible types.  Row
    count is **not** gated, and zero rows yields ``unsure`` rather than
    ``fail`` -- the 100-patient demo cohort legitimately holds nothing for
    some concepts (``neuroblock`` has 0 demo rows and 14,174 on full data).
    A shape pass earns nothing but permission to spend an HPC run.

``full``
    The **correctness** gate.  Runs on HPC against the immutable oracle.
    Schema identity, then a keyed row-level diff that *classifies* every
    divergence rather than merely counting it.

Everything is computed as SQL inside DuckDB; rows are never materialised into
Python.  ``vitalsign`` is 9.7M rows and ``rhythm`` 5.9M, so the previous
whole-table-JSON contract was not a tuning problem but the wrong shape.

Per-column min/max identity is deliberately *not* a gate.  A port that
computes every value correctly but attaches it to the wrong key satisfies row
count, schema, min and max simultaneously.  The keyed diff is what
substantiates equivalence, and it reports *which column* differs -- so a
diagnosis can say "``age`` differs on 1,204 rows" instead of "counts differ".

Row count is **not** a hard gate
--------------------------------

MIMIC-on-FHIR does not carry everything relational MIMIC-IV carries, so a
candidate can be a faithful port and still return fewer rows.  An exact row
count is therefore evidence, not a verdict, and the comparator does not decide
those cases -- the equivalence judge does.

What the comparator *must* do is hand the judge something sharper than "counts
differ by 12,043", because that number alone cannot distinguish a legitimate
coverage gap from a botched window.  The keyed diff decomposes it:

============================  ==========================================
class                         what can cause it?
============================  ==========================================
``only_oracle``               a coverage gap -- this is its shape
``differing_null_only``       a coverage gap -- the element does not exist
``only_candidate``            a port bug (fan-out, wrong filter), **or**
                              an upstream ETL row the oracle SQL excludes
``differing_conflict``        a port bug, **or** upstream transformation
                              loss -- MIMIC-on-FHIR carries a *different*
                              value that no SQL can invert
============================  ==========================================

The last row is the correction this taxonomy needed.  MIMIC-on-FHIR is not a
*subset* of MIMIC-IV, it is a **transform** of it: ``fhir_patient.sql``
synthesises ``Patient.birthDate`` from ``MIN(transfers.intime) - anchor_age``
rather than ``anchor_year - anchor_age``, and ``fhir_encounter.sql`` casts
admission times through ``TIMESTAMPTZ``, which collapses DST-gap wall times.
Both produce key-matched rows whose values disagree, and neither is a port bug
-- no candidate query can recover a value the ETL destroyed.  So a conflict is
*not* self-evidently wrong, and hard-failing it fails faithful ports.

The comparator cannot tell a bug from transformation loss: both look identical
in the data.  What it can do is say which of the two shapes it saw, and hand
the case to the judge at the right evidentiary bar.  Hence a three-valued
verdict and a two-tier ``review``:

``match``
    Nothing diverged.  The judge is **not** called.
``mismatch``
    A machine-provable contradiction: the candidate did not execute, the
    schema is wrong, or the port contradicted its own declaration.  There is
    nothing to weigh, so the judge is **not** called.
``review``
    Divergence the judge decides, carrying ``divergence.tier``:

    ``gap_shaped``
        Only ``only_oracle`` / ``differing_null_only``.  An accept must name
        the absent FHIR element.
    ``contested``
        ``differing_conflict`` or ``only_candidate`` is present.  Same
        verdict, **higher bar**: an accept must cite the upstream ETL
        statement that makes the oracle value unrecoverable, not merely an
        absence.  ``divergence.judge_bar`` spells this out in the artifact.
    ``attributed``
        ``differing_conflict`` was the *only* contested class and the
        comparator **replayed** it to a known upstream transformation over
        every conflicting row -- see "Attributing a conflict" below.  Still
        ``review``, still judged; what changes is that the citation the
        ``contested`` bar demands is already in the artifact, so there is
        nothing for a diagnosis to derive.

Attributing a conflict
----------------------

``mimic-fhir`` casts naive MIMIC wall-clock times through ``TIMESTAMPTZ``
before writing them into a resource.  For a wall time in the DST spring-forward
gap that cast is not the identity -- 02:10 on a March Sunday becomes 03:10 --
and the original is unrecoverable.  It is also *replayable*: round-tripping the
oracle value through ``America/New_York`` reproduces exactly what the ETL wrote.

So the comparator does that, per row, over the whole conflict set, and a
conflict set it explains completely moves to tier ``attributed``.  This is
strictly stronger evidence than a model inferring the same thing from a bounded
sample -- and much cheaper, since the diagnosis it replaces was 72% of the
loop's token spend.

Deliberate limits, all of them stated in ``divergence.judge_bar``:

* Attribution never yields ``match`` and never skips the judge.  The values do
  differ from the oracle; accepting that is a ruling, not an arithmetic fact.
* All-or-nothing.  A partially explained conflict set stays ``contested`` --
  the unexplained rows decide the bar -- though the artifact records which rows
  are already accounted for.
* It proves the *operation*, not the *provenance*.  The citation list is the
  set of known ETL sites, not a per-column proof, and the judge confirms which
  one applies.
* A large attributed fraction is evidence **against** the attribution: DST-gap
  wall times are one hour a year.  The judge is told to answer ``bug`` when the
  fraction is not consistent with that rarity.
* If the zone rules available at comparison time do not reproduce the ETL's, a
  canary catches it and nothing is attributed.

Columns with no FHIR representation
-----------------------------------

Some oracle columns cannot be produced at all -- ``age.anchor_year`` survives
in MIMIC-on-FHIR only inside ``Patient.birthDate``, collapsed with
``anchor_age`` into their difference.  The contract's answer is a **typed NULL,
never an estimate**: NULL lands in ``differing_null_only`` and reaches the
judge, whereas a 99%-accurate guess lands in ``differing_conflict`` and is
blocking.  The more diligent-looking choice is the failing one, so the port
declares such columns in ``unrepresentable.json`` (column -> justification) and
this comparator *verifies* the claim -- a declared column that is not 100% NULL
in the candidate is itself a blocking failure.  The declaration never upgrades
a verdict; it attaches a stated reason to the divergence the judge must rule on.

A confirmed declaration does change one *number*, though.  A column that is
100% NULL by design makes every single row "differing", so ``age`` reports
``0 of 431,231 rows reproduced identically`` while in fact reproducing every
representable value on 430,727 of them.  The headline figure is then an
artifact of the declaration rather than a statement about the port, so the
result also carries ``identical_representable`` / ``representable_fraction``:
the same count computed over the columns the port was ever able to produce.
Both are reported; neither replaces the other.

Concepts with no unique key
---------------------------

The 13 concepts with no unique key are compared as full-tuple multisets, where
the classification above is not directly computable: a NULL where the oracle
holds a value appears in ``only_oracle`` *and* ``only_candidate`` at once,
indistinguishable from an invented row.

Two counts are emphatically **not** the way out of that, because they are not
independent.  ``EXCEPT ALL`` is multiset difference, so

    |only_oracle| - |only_candidate| == oracle_rows - candidate_rows

*identically*.  Whenever the row counts match, the two divergence counts are
equal -- for every candidate, however wrong.  "``only_oracle`` and
``only_candidate`` are both 3,182, so the rows must be paired substitutions
rather than invented rows" is therefore not a weak argument but a vacuous one,
and it is an easy argument to make by accident.

So the residual is paired *explicitly*: ``_residual_pairing`` searches for a
small column set ``D`` such that the two residuals are equal as multisets once
``D`` is projected away.  When one exists and the remaining columns are
anchored by an identity column, the residual is "the same rows differing in
``D``", every substituted column is classified exactly as the keyed diff would
classify it, and the result carries ``classification: paired_residual``.  When
none exists, the rows genuinely do not correspond, the result keeps
``classification: unavailable_no_key``, and the judge is told both that it is
reasoning with less evidence and that the count equality is not the missing
evidence.
"""

from __future__ import annotations

import argparse
import glob
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

DERIVED_SCHEMA = "mimiciv_derived"

# Tolerances apply to *values* only, never to row count.
DEFAULT_RTOL = 0.001  # 0.1 % relative
DEFAULT_ATOL = 1e-6
TIMESTAMP_TOL_SECONDS = 1.0

DEFAULT_SAMPLE_LIMIT = 20

# ---------------------------------------------------------------------------
# Type classification
#
# Spans DuckDB (oracle) and Spark/Pathling (candidate) type vocabularies, which
# name the same logical types differently -- BIGINT vs long, DOUBLE vs double,
# VARCHAR vs string.
# ---------------------------------------------------------------------------

_INTEGER_TYPES = frozenset(
    {
        "int2", "int4", "int8", "smallint", "integer", "bigint",
        "tinyint", "byte", "short", "int", "long",
        "hugeint", "uhugeint", "utinyint", "usmallint", "uinteger", "ubigint",
        "oid", "xid", "cid", "tid",
    }
)
_NUMERIC_TYPES = frozenset(
    {
        "float4", "float8", "float", "double", "numeric", "decimal",
        "real", "double precision", "money",
    }
)
_BOOLEAN_TYPES = frozenset({"bool", "boolean"})
_STRING_TYPES = frozenset(
    {"text", "string", "varchar", "char", "bpchar", "name", "citext", "uuid"}
)
_BINARY_TYPES = frozenset({"bytea", "blob", "binary", "varbinary"})
_DATETIME_TYPES = frozenset(
    {
        "timestamp", "timestamp_ntz", "timestamptz", "datetime",
        "timestamp without time zone", "timestamp with time zone",
        "timestamp_s", "timestamp_ms", "timestamp_ns",
    }
)
_DATE_TYPES = frozenset({"date"})
_TIME_TYPES = frozenset({"time", "timetz", "time without time zone", "time with time zone"})
_INTERVAL_TYPES = frozenset({"interval"})


def _normalise_type(type_name: str) -> str:
    """Strip precision/parameters and lowercase: ``DECIMAL(10,2)`` -> ``decimal``."""
    return type_name.lower().split("(")[0].strip()


def classify_logical_type(type_name: str) -> str:
    """Map a DuckDB or Spark type name onto a logical category."""
    t = _normalise_type(type_name)
    if t in _INTEGER_TYPES:
        return "integer"
    if t in _NUMERIC_TYPES:
        return "numeric"
    if t in _BOOLEAN_TYPES:
        return "boolean"
    if t in _DATETIME_TYPES:
        return "datetime"
    if t in _DATE_TYPES:
        return "date"
    if t in _TIME_TYPES:
        return "time"
    if t in _INTERVAL_TYPES:
        return "interval"
    if t in _STRING_TYPES:
        return "string"
    if t in _BINARY_TYPES:
        return "binary"
    if t.startswith(("struct", "map", "list", "array")) or t.endswith("[]"):
        return "nested"
    if t in ("json", "jsonb"):
        return "json"
    return "other"


def types_compatible(type_a: str, type_b: str) -> bool:
    """Logical compatibility across the DuckDB / Spark type vocabularies."""
    if _normalise_type(type_a) == _normalise_type(type_b):
        return True
    cat_a = classify_logical_type(type_a)
    cat_b = classify_logical_type(type_b)
    if cat_a == cat_b:
        return True
    # Numeric widening is acceptable; SMALLINT vs BIGINT vs DOUBLE all carry
    # the same values for these concepts.
    if {cat_a, cat_b} <= {"integer", "numeric"}:
        return True
    # Pathling frequently returns a timestamp where the oracle stores a date.
    if {cat_a, cat_b} <= {"datetime", "date"}:
        return True
    return False


# ---------------------------------------------------------------------------
# SQL construction
# ---------------------------------------------------------------------------


def _q(identifier: str) -> str:
    """Quote a SQL identifier."""
    return '"' + identifier.replace('"', '""') + '"'


def _lit(value: str) -> str:
    """Quote a SQL string literal."""
    return "'" + str(value).replace("'", "''") + "'"


def scan_expression(path: str | Path) -> str:
    """A DuckDB scan expression for a candidate result file.

    Both legs write Parquet -- a directory of Spark part-files, addressed by a
    ``.../*.parquet`` glob -- because Parquet carries the Spark schema and a
    text format does not.  NDJSON and CSV stay supported for hand-driven
    ``compare-port-results`` invocations, but note that DuckDB must *infer*
    their types: an all-null column infers as ``JSON`` and a DECIMAL as
    ``VARCHAR``, so a type verdict from a text candidate is about the file, not
    about the query that produced it.

    Either way the file is read natively, so nothing is loaded through Python.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix in (".parquet", ".pq"):
        return f"read_parquet({_lit(str(p))})"
    if suffix in (".ndjson", ".jsonl", ".json"):
        return f"read_json_auto({_lit(str(p))}, format='newline_delimited')"
    if suffix == ".csv":
        return f"read_csv_auto({_lit(str(p))})"
    raise ValueError(
        f"Unsupported candidate format {suffix!r}: expected .parquet, .ndjson, "
        f".jsonl, .json or .csv"
    )


def _column_equality_sql(column: str, type_name: str, rtol: float, atol: float) -> str:
    """SQL boolean: is this column equal between oracle ``o`` and candidate ``c``?

    NULL == NULL is true (``IS NOT DISTINCT FROM`` semantics), because a NULL
    in the oracle must be reproduced as a NULL, not as a value.
    """
    o, c = f"o.{_q(column)}", f"c.{_q(column)}"
    both_null = f"({o} IS NULL AND {c} IS NULL)"
    both_present = f"({o} IS NOT NULL AND {c} IS NOT NULL)"
    category = classify_logical_type(type_name)

    if category in ("numeric",):
        close = (
            f"abs({o} - {c}) <= greatest({rtol} * greatest(abs({o}), abs({c})), {atol})"
        )
        return f"({both_null} OR ({both_present} AND {close}))"

    if category == "datetime":
        close = (
            f"abs(epoch({o}) - epoch({c})) <= {TIMESTAMP_TOL_SECONDS}"
        )
        return f"({both_null} OR ({both_present} AND {close}))"

    # Integers, strings, booleans, dates, times, binary: exact.
    return f"({o} IS NOT DISTINCT FROM {c})"


def _column_candidate_null_sql(column: str) -> str:
    """SQL boolean: the oracle holds a value here and the candidate holds NULL.

    The one value-level divergence a coverage gap can legitimately produce: the
    row exists in FHIR, but the element carrying this column does not.  Kept
    separate from every other inequality because it is the only one the judge
    is allowed to consider.
    """
    return f"(o.{_q(column)} IS NOT NULL AND c.{_q(column)} IS NULL)"


def _column_conflict_sql(column: str, type_name: str, rtol: float, atol: float) -> str:
    """SQL boolean: this column diverges in a way a coverage gap cannot explain.

    Everything that is not equal and not a candidate-side NULL: both sides hold
    a value and they disagree, or the candidate invented a value where the
    oracle holds NULL.  Neither is survivable by "MIMIC-on-FHIR has less data".
    """
    equal = _column_equality_sql(column, type_name, rtol, atol)
    return f"(NOT {equal} AND NOT {_column_candidate_null_sql(column)})"


# ---------------------------------------------------------------------------
# Upstream-ETL attribution
#
# A `differing_conflict` is the one class the comparator has never been able to
# explain, because a port bug and upstream transformation loss look identical in
# the data.  For *one* upstream transformation that is no longer true.
#
# `mimic-fhir` casts naive MIMIC wall-clock times through `TIMESTAMPTZ` before
# writing them into a FHIR resource (`fhir_encounter.sql:65`,
# `fhir_medication_request.sql:43-44`).  For a wall time inside the DST
# spring-forward gap that cast is not the identity: the nonexistent 02:10 on a
# March Sunday normalises to 03:10, and the original is gone.
#
# That operation is *replayable*.  Round-tripping the oracle value through the
# same zone reproduces exactly what the ETL wrote, so the comparator can prove
# -- per row, over every conflicting row rather than a sample -- that the
# candidate holds the value the ETL produced from the oracle value, and not some
# other value the port got wrong.  A conflict that replays is not a port bug,
# and saying so here is strictly stronger than a model inferring it from a
# bounded sample of "differs by an hour".
#
# What this does NOT establish, and the judge is told so explicitly:
#
# * *which* upstream statement wrote this concept's element.  The citation list
#   is the set of known sites, not a per-column proof.
# * that the shape is plausible.  DST-gap rows are rare by construction, so a
#   large attributed fraction is evidence the replay is coincidental, not
#   evidence of transformation loss.
#
# Attribution therefore never produces `match` and never skips the judge.  It
# lowers the evidentiary bar on a class it has discharged the arithmetic for,
# and it lets the loop skip a diagnosis whose entire content would have been
# re-deriving this paragraph.
# ---------------------------------------------------------------------------

#: The zone the upstream ETL's `TIMESTAMPTZ` casts resolve against. MIMIC is a
#: Boston dataset and the ETL runs without an explicit zone, so the naive
#: value is interpreted as US Eastern local time.
UPSTREAM_TZ = "America/New_York"

_DST_REPLAY_CAUSE = "upstream_timestamptz_dst_shift"

_DST_REPLAY_OPERATION = (
    "For every conflicting row, the candidate value equals the oracle value "
    f"round-tripped through a {UPSTREAM_TZ} TIMESTAMPTZ cast "
    "(`timezone(tz, timezone(tz, oracle))`), and differs from the oracle only "
    "where that round-trip is not the identity -- i.e. the oracle wall time "
    "falls in the DST spring-forward gap. This is the operation the upstream "
    "mimic-fhir ETL performs before writing the FHIR element, replayed and "
    "checked row by row over the whole conflict set, not sampled."
)

#: Known `mimic-fhir` statements that perform the cast. Not exhaustive, and not
#: resolved per column -- the judge confirms which one applies here.
_DST_REPLAY_CITATIONS = (
    "mimic-fhir/sql/fhir_encounter.sql:65",
    "mimic-fhir/sql/fhir_medication_request.sql:43-44",
)

#: A DST-gap wall time and an ordinary one. The replay must shift the first by
#: exactly one hour and leave the second alone; anything else means the zone
#: rules available here are not the ones the ETL used, and nothing is attributed.
_DST_CANARY = (
    ("2153-03-11 02:30:00", "2153-03-11 03:30:00"),
    ("2154-05-02 15:55:21", "2154-05-02 15:55:21"),
)


def _tz_roundtrip_sql(expr: str) -> str:
    """The upstream cast, replayed: naive -> zoned -> naive in ``UPSTREAM_TZ``."""
    tz = _lit(UPSTREAM_TZ)
    return f"timezone({tz}, timezone({tz}, CAST({expr} AS TIMESTAMP)))"


def _dst_replay_column_sql(column: str) -> str:
    """SQL boolean: this column's conflict *is* the upstream DST shift.

    Both sides hold a value, the candidate matches the oracle value replayed
    through the upstream cast, and it differs from the oracle itself -- so the
    row is inside the gap rather than merely surviving a no-op round-trip.
    Compared at the comparator's own timestamp tolerance, not exactly, so
    attribution and the conflict tally cannot disagree about a sub-second edge.
    """
    o, c = f"o.{_q(column)}", f"c.{_q(column)}"
    replay = _tz_roundtrip_sql(o)
    c_epoch = f"epoch(CAST({c} AS TIMESTAMP))"
    return (
        f"({o} IS NOT NULL AND {c} IS NOT NULL"
        f" AND abs({c_epoch} - epoch({replay})) <= {TIMESTAMP_TOL_SECONDS}"
        f" AND abs({c_epoch} - epoch(CAST({o} AS TIMESTAMP)))"
        f" > {TIMESTAMP_TOL_SECONDS})"
    )


def _dst_replay_available(con: Any) -> Optional[str]:
    """``None`` when the replay is trustworthy here, else why it is not.

    Named-zone arithmetic is DuckDB's ICU extension, which the Python wheel
    bundles and autoloads. `LOAD` is attempted anyway and **`INSTALL` is
    deliberately not**: the comparison runs inside a Slurm job on a compute node
    that may have no egress, and a blocking extension fetch would burn the run's
    wall clock. Not attributing costs one diagnostician; a hung comparison costs
    the whole HPC run.

    There is also no fallback to a hand-rolled "second Sunday in March" rule.
    A weaker proof carried under the same tier name is exactly the erosion this
    tier has to avoid -- if the zone database is not here, the conflict stays
    `contested` and the diagnostician does the work it does today.

    The canary is then checked explicitly rather than trusting the load, because
    an extension that resolves the zone differently than the ETL's zone database
    did must not be allowed to attribute anything either.
    """
    try:
        con.execute("LOAD icu")
    except Exception:  # noqa: BLE001 - bundled/autoloaded builds need no LOAD
        pass

    for naive, expected in _DST_CANARY:
        try:
            got = con.execute(
                f"SELECT {_tz_roundtrip_sql(f'TIMESTAMP {_lit(naive)}')}"
            ).fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            return (
                f"named-zone arithmetic unavailable ({exc}); the upstream "
                "TIMESTAMPTZ cast cannot be replayed. Fix by making DuckDB's "
                "`icu` extension available where the comparison runs (a one-off "
                "`INSTALL icu`, or ship it with the job) -- it is never "
                "installed from inside the comparison"
            )
        if got is None or str(got)[:19] != expected:
            return (
                f"zone canary failed: {UPSTREAM_TZ} maps {naive} to {got!r}, "
                f"expected {expected!r}. The DST rules available here are not "
                "the ones the upstream ETL used, so a replay would prove nothing"
            )
    return None


def _attribute_dst_conflicts(
    con: Any,
    *,
    cte: str,
    from_sql: str,
    row_conflict: str,
    conflict_by_column: Dict[str, str],
    types_by_column: Dict[str, str],
    sample_select: str,
    sample_limit: int,
) -> Dict[str, Any]:
    """How much of the conflict set is the upstream DST shift, and which columns.

    *cte* / *from_sql* are the caller's row-alignment scaffolding, so the keyed
    join and the paired residual are attributed by the same predicate over their
    own alignment. *conflict_by_column* must be the very expressions the caller
    tallied ``differing_conflict`` from -- attribution partitions that set, it
    does not recompute it.
    """
    datetime_columns = sorted(
        name
        for name in conflict_by_column
        if classify_logical_type(types_by_column.get(name, "")) == "datetime"
    )
    if not datetime_columns:
        return {
            "attempted": False,
            "complete": False,
            "why": "no datetime column in this concept; the DST cast cannot apply",
        }

    unavailable = _dst_replay_available(con)
    if unavailable:
        return {"attempted": False, "complete": False, "why": unavailable}

    replay_by_column = {name: _dst_replay_column_sql(name) for name in datetime_columns}

    # A row is attributed only if EVERY column it conflicts on replays. One
    # conflict in a non-datetime column, or in a datetime column the replay does
    # not explain, leaves the whole row unattributed -- the row is the unit the
    # tier is decided on, so partial explanation must not count.
    per_column = [
        f"(NOT {conflict} OR {replay_by_column[name]})"
        if name in replay_by_column
        else f"(NOT {conflict})"
        for name, conflict in sorted(conflict_by_column.items())
    ]
    attributed = f"({row_conflict}) AND ({' AND '.join(per_column)})"

    tallies = ",\n  ".join(
        f'count(*) FILTER (WHERE {attributed} AND {conflict_by_column[name]}) '
        f'AS {_q("a__" + name)}'
        for name in datetime_columns
    )
    row = con.execute(
        f"{cte} SELECT\n"
        f"  count(*) FILTER (WHERE {row_conflict}) AS conflict_rows,\n"
        f"  count(*) FILTER (WHERE {attributed}) AS attributed_rows,\n"
        f"  {tallies}\n{from_sql}"
    ).fetchone()
    counts = dict(zip([d[0] for d in con.description], row))

    conflict_rows = counts["conflict_rows"] or 0
    attributed_rows = counts["attributed_rows"] or 0
    result: Dict[str, Any] = {
        "attempted": True,
        "cause": _DST_REPLAY_CAUSE,
        "operation": _DST_REPLAY_OPERATION,
        "timezone": UPSTREAM_TZ,
        "citations": list(_DST_REPLAY_CITATIONS),
        "columns_considered": datetime_columns,
        "conflict_rows": conflict_rows,
        "attributed_rows": attributed_rows,
        "residual_rows": conflict_rows - attributed_rows,
        # `complete` is the only field that moves a tier, and it is deliberately
        # all-or-nothing: a partially attributed conflict set still holds rows
        # nothing has explained, and those rows decide the bar.
        "complete": bool(conflict_rows) and attributed_rows == conflict_rows,
        "columns": dict(
            sorted(
                ((name, counts["a__" + name]) for name in datetime_columns
                 if counts.get("a__" + name)),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ),
    }
    if attributed_rows and sample_limit > 0:
        replay_select = "".join(
            f", {_tz_roundtrip_sql('o.' + _q(name))} AS {_q(name + '__replayed')}"
            for name in datetime_columns
        )
        cur = con.execute(
            f"{cte} SELECT {sample_select}{replay_select}\n{from_sql}\n"
            f"WHERE {attributed}\nLIMIT {int(sample_limit)}"
        )
        cols = [d[0] for d in cur.description]
        result["samples"] = [dict(zip(cols, r)) for r in cur.fetchall()]
    return result


# ---------------------------------------------------------------------------
# Manifest access
# ---------------------------------------------------------------------------


def load_manifest_entry(manifest_path: str | Path, concept: str) -> Dict[str, Any]:
    """Load one concept's entry from the oracle manifest."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    concepts = manifest.get("concepts", {})
    if concept not in concepts:
        raise ValueError(
            f"Concept {concept!r} not in manifest {manifest_path}. "
            f"Known: {sorted(concepts)[:8]}{'...' if len(concepts) > 8 else ''}"
        )
    entry = dict(concepts[concept])
    entry["_dataset"] = manifest.get("dataset", "")
    entry["_oracle"] = manifest.get("oracle", {})
    return entry


def _candidate_columns(con: Any, scan: str) -> Dict[str, str]:
    """``{column: type}`` for the candidate, in physical order."""
    rows = con.execute(f"DESCRIBE SELECT * FROM {scan}").fetchall()
    return {r[0]: r[1] for r in rows}


_ID_COLUMNS = frozenset({"subject_id", "hadm_id", "stay_id"})


def _schema_hints(incompatible: Sequence[Dict[str, str]]) -> list[str]:
    """Name the known cause of a type mismatch, where there is exactly one.

    A string-vs-number mismatch has a single cause in this loop: everything a
    ViewDefinition produces is a Spark STRING, and the outermost SELECT did not
    CAST it to the manifest type.  Saying so in the report turns a diagnosis
    that otherwise costs a round of warehouse probing into a read -- the
    remedy travels with the failure instead of being rederived from it.
    """
    hints: list[str] = []
    for item in incompatible:
        if classify_logical_type(item["actual"]) != "string":
            continue
        if classify_logical_type(item["expected"]) not in {
            "integer",
            "numeric",
            "datetime",
            "date",
        }:
            continue
        hint = (
            f"{item['column']}: candidate is {item['actual']} where the manifest "
            f"declares {item['expected']}. A ViewDefinition yields Spark STRINGs; "
            f"the outermost SELECT must CAST every column to its manifest type "
            f"(see the `pathling-sql` skill)."
        )
        if item["column"] in _ID_COLUMNS:
            hint += (
                " This is an identifier column: also check that the FHIRPath is "
                "`identifier.value` for the right identifier.system and not "
                "getResourceKey()/getReferenceKey(), which yield UUIDs no cast "
                "can rescue (see `fhir-mapping` -> Identifier spine, and the "
                "identifier entry in MIMIC_NOTES.md)."
            )
        hints.append(hint)
    return hints


def _compare_schemas(
    expected: Sequence[Dict[str, str]], actual: Dict[str, str]
) -> Dict[str, Any]:
    """Column name and type comparison against the manifest."""
    expected_names = [c["name"] for c in expected]
    expected_types = {c["name"]: c["type"] for c in expected}

    missing = [n for n in expected_names if n not in actual]
    extra = [n for n in actual if n not in expected_types]

    incompatible = []
    for name in expected_names:
        if name in actual and not types_compatible(expected_types[name], actual[name]):
            incompatible.append(
                {"column": name, "expected": expected_types[name], "actual": actual[name]}
            )

    result: Dict[str, Any] = {
        "expected_columns": expected_names,
        "actual_columns": list(actual),
        "missing_columns": missing,
        "extra_columns": extra,
        "incompatible_types": incompatible,
        "match": not missing and not extra and not incompatible,
    }
    hints = _schema_hints(incompatible)
    if hints:
        result["hints"] = hints
    return result


# ---------------------------------------------------------------------------
# Declared-unrepresentable columns
#
# Some oracle columns have no MIMIC-on-FHIR representation at all -- not "the
# element is null for these rows" but "no element carries this, ever".
# `age.anchor_year` is the worked example: MIMIC-on-FHIR stores only
# `Patient.birthDate`, whose year is `anchor_year - anchor_age`, so the pair is
# collapsed to its difference and cannot be recovered.
#
# The contract's answer is to emit a typed NULL, never an estimate: a NULL
# lands in `differing_null_only` (reviewable), while a 99%-accurate guess lands
# in `differing_conflict` (blocking, unoverridable). Declaring the column here
# turns that choice from intent the judge must infer into a claim the
# comparator machine-checks -- and a false declaration is itself blocking.
# ---------------------------------------------------------------------------

#: Attempt-directory filename holding the declaration.
UNREPRESENTABLE_FILENAME = "unrepresentable.json"

#: A justification must name the element or path. Short strings ("n/a", "none")
#: are the failure mode this guards against.
_MIN_JUSTIFICATION_CHARS = 20


class UnrepresentableDeclarationError(ValueError):
    """The declaration file is missing, malformed, or internally inconsistent."""


def load_unrepresentable(path: str | Path) -> Dict[str, str]:
    """Read and shape-check ``unrepresentable.json``.

    Maps column name -> justification. The justification is prose naming the
    FHIR element or path that is absent; it is copied into the comparison
    artifact so the judge rules on a stated claim rather than on silence.
    """
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise UnrepresentableDeclarationError(f"Declaration not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise UnrepresentableDeclarationError(f"{path} is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict):
        raise UnrepresentableDeclarationError(
            f"{path} must be a JSON object mapping column name -> justification, "
            f"got {type(raw).__name__}"
        )
    for column, justification in raw.items():
        if not isinstance(justification, str) or len(justification.strip()) < _MIN_JUSTIFICATION_CHARS:
            raise UnrepresentableDeclarationError(
                f"{path}: column {column!r} needs a justification of at least "
                f"{_MIN_JUSTIFICATION_CHARS} characters naming the missing FHIR "
                f"element or path; got {justification!r}"
            )
    return {str(k): v.strip() for k, v in raw.items()}


def _verify_unrepresentable(
    declared: Dict[str, str],
    entry: Dict[str, Any],
    con: Any,
    scan: str,
) -> Dict[str, Any]:
    """Check every declared column against the manifest and the candidate data.

    A declaration is only worth anything if it is falsifiable, so all three
    ways it can be wrong are checked:

    * the column is not in the oracle schema (typo, or a stale declaration
      left behind after the manifest moved);
    * the column is part of the natural key (the join would be impossible, so
      the claim is incoherent rather than merely unsupported);
    * the candidate emitted a value for it anyway, which contradicts the claim
      -- this is the 99%-heuristic case the contract exists to prevent.

    Columns that are fully NULL but *not* declared are reported too. They are
    not a failure, but they are exactly what an undeclared representation gap
    looks like, and the judge should see them.
    """
    manifest_columns = {c["name"] for c in entry["columns"]}
    key = set(entry.get("key") or [])

    violations: List[Dict[str, Any]] = []
    confirmed: Dict[str, str] = {}

    for column in sorted(declared):
        if column not in manifest_columns:
            violations.append({
                "column": column,
                "reason": "not a column of this concept in the oracle manifest",
            })
            continue
        if column in key:
            violations.append({
                "column": column,
                "reason": (
                    "is part of the natural key; a key column cannot be "
                    "unrepresentable or the keyed diff could not align rows"
                ),
            })
            continue
        non_null = con.execute(
            f"SELECT count({_q(column)}) FROM {scan}"
        ).fetchone()[0]
        if non_null:
            violations.append({
                "column": column,
                "reason": (
                    f"declared unrepresentable but the candidate emitted "
                    f"{non_null:,} non-NULL value(s). Emit a typed NULL "
                    f"(CAST(NULL AS <type>)) rather than an estimate, or "
                    f"withdraw the declaration"
                ),
                "non_null_rows": non_null,
            })
            continue
        confirmed[column] = declared[column]

    # Fully-NULL columns nobody declared: the shape of an unreported gap.
    undeclared: List[str] = []
    for column in sorted(manifest_columns - key - set(declared)):
        non_null = con.execute(f"SELECT count({_q(column)}) FROM {scan}").fetchone()[0]
        if non_null == 0:
            undeclared.append(column)

    return {
        "declared": declared,
        "confirmed": confirmed,
        "violations": violations,
        "undeclared_fully_null_columns": undeclared,
        "policy": (
            "A declared column must be 100% NULL in the candidate. Declaring a "
            "column and then emitting an estimate for it is blocking: it "
            "converts a reviewable coverage gap into a value conflict."
        ),
    }


# ---------------------------------------------------------------------------
# Mode: shape (the demo gate)
# ---------------------------------------------------------------------------


def _schema_is_uninferable(candidate_path: str | Path) -> bool:
    """True when nothing can be read from the candidate, so it carries no schema.

    Two ways to reach this state, both meaning "the port returned nothing":

    * a zero-row NDJSON or CSV, which is a 0-byte file;
    * a Parquet glob that matches no part-files, which is what Spark leaves
      behind when it writes an empty DataFrame with no partitions.

    Used to tell "the port returned nothing" apart from "the port returned the
    wrong columns", which would otherwise be indistinguishable and fail the
    concept. A Parquet directory that *does* hold part-files carries its schema
    even at zero rows, so it is inferable and the columns still get checked.
    """
    raw = str(candidate_path)
    try:
        if any(ch in raw for ch in "*?["):
            return not glob.glob(raw)
        path = Path(raw)
        return path.is_file() and path.stat().st_size == 0
    except OSError:
        return False


def compare_shape(
    concept: str,
    manifest_path: str | Path,
    candidate_path: str | Path,
) -> Dict[str, Any]:
    """Demo shape gate: did it execute, and are the columns right?

    Returns a verdict of ``shape_ok``, ``shape_fail`` or ``unsure``.  Row count
    is reported but **never** gated, and zero rows is ``unsure`` -- see
    LOOP_CONTRACT.md.
    """
    import duckdb

    entry = load_manifest_entry(manifest_path, concept)
    result: Dict[str, Any] = {
        "format_version": "2.0",
        "mode": "shape",
        "concept": concept,
        "dataset": "demo",
        "candidate": str(candidate_path),
        "gated": ["execution", "column_names", "column_types"],
        "not_gated": ["row_count"],
    }

    con = duckdb.connect(":memory:")
    try:
        scan = scan_expression(candidate_path)

        # An empty candidate is decided BEFORE anything is read, and the order
        # is the whole point. A candidate that carries no schema at all cannot
        # be *scanned*, let alone described -- an empty NDJSON file reads as a
        # single column named `json`, and a Parquet glob matching no part-files
        # raises. Either would be reported as the wrong columns, blocking
        # exactly the concepts the contract protects: `neuroblock` has 0 demo
        # rows and 14,174 on full data, and must reach the HPC run rather than
        # die at the demo gate.
        result["oracle_full_row_count"] = entry["row_count"]
        if _schema_is_uninferable(candidate_path):
            result["executed"] = True
            result["candidate_row_count"] = 0
            result["schema"] = {"match": None, "checked": False}
            result["verdict"] = "unsure"
            result["note"] = (
                "0 demo rows and no schema in the candidate: the 100-patient "
                "cohort may legitimately contain nothing for this concept. Not "
                "a failure. Proceed to full data."
            )
            return result

        try:
            actual = _candidate_columns(con, scan)
            row_count = con.execute(f"SELECT count(*) FROM {scan}").fetchone()[0]
        except Exception as exc:  # noqa: BLE001 -- reported as the verdict
            result["executed"] = False
            result["error"] = str(exc)
            result["verdict"] = "shape_fail"
            return result

        result["executed"] = True
        # Observation only. Demo agreement is not evidence of correctness and
        # demo disagreement on count is not proof of a bug.
        result["candidate_row_count"] = row_count

        # Parquet carries its schema even with no rows, so a zero-row candidate
        # still gets its columns checked -- the verdict is `unsure` either way,
        # because row count is never a demo gate.
        if row_count == 0:
            result["schema"] = _compare_schemas(entry["columns"], actual)
            result["verdict"] = "unsure"
            result["note"] = (
                "0 demo rows: the 100-patient cohort may legitimately contain "
                "nothing for this concept. Not a failure. Proceed to full data."
            )
            return result

        result["schema"] = _compare_schemas(entry["columns"], actual)
        if not result["schema"]["match"]:
            result["verdict"] = "shape_fail"
        else:
            result["verdict"] = "shape_ok"
            result["note"] = (
                "Shape is correct. This earns permission to spend an HPC run; "
                "it is not evidence of correctness."
            )
        return result
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Mode: full (the correctness gate)
# ---------------------------------------------------------------------------


def _keyed_diff(
    con: Any,
    oracle_ref: str,
    scan: str,
    key: Sequence[str],
    value_columns: Sequence[Dict[str, str]],
    rtol: float,
    atol: float,
    sample_limit: int,
    representable_only: frozenset = frozenset(),
) -> Dict[str, Any]:
    """Full outer join on the natural key, then per-column value comparison.

    Key-matched rows are split three ways rather than two, because "differing"
    conflates a divergence sourced in a coverage gap (the candidate is NULL
    where the oracle has a value -- the FHIR element is absent) with one that
    is not (both sides hold a value and disagree).  Collapsing them would force
    the judge to argue from a number that cannot support the argument.

    *representable_only* names the columns whose unrepresentability the
    comparator has already **confirmed** -- 100% NULL, as declared.  Those
    columns are excluded from a second identity tally, because a by-design NULL
    column makes every row differ and drives the headline identity fraction to
    zero regardless of how good the port is.
    """
    join_on = " AND ".join(f"o.{_q(k)} = c.{_q(k)}" for k in key)
    anchor = _q(key[0])
    both = f"o.{anchor} IS NOT NULL AND c.{anchor} IS NOT NULL"

    eq_by_column = {
        col["name"]: _column_equality_sql(col["name"], col["type"], rtol, atol)
        for col in value_columns
    }
    conflict_by_column = {
        col["name"]: _column_conflict_sql(col["name"], col["type"], rtol, atol)
        for col in value_columns
    }
    null_by_column = {
        col["name"]: _column_candidate_null_sql(col["name"]) for col in value_columns
    }

    all_equal = " AND ".join(eq_by_column.values()) if eq_by_column else "TRUE"
    any_conflict = " OR ".join(conflict_by_column.values()) if conflict_by_column else "FALSE"
    any_null = " OR ".join(null_by_column.values()) if null_by_column else "FALSE"

    # Identity restricted to the columns the port could ever have produced.
    representable_eq = [
        expr for name, expr in eq_by_column.items() if name not in representable_only
    ]
    representable_equal = " AND ".join(representable_eq) if representable_eq else "TRUE"

    # A row is classified by its worst column: one real conflict makes the whole
    # row a conflict, however many merely-NULL columns it also has.
    row_conflict = f"{both} AND ({any_conflict})"
    row_null_only = f"{both} AND NOT ({any_conflict}) AND ({any_null})"

    tallies = ",\n  ".join(
        [
            f'count(*) FILTER (WHERE {both} AND {expr}) AS {_q("k__" + name)}'
            for name, expr in conflict_by_column.items()
        ]
        + [
            f'count(*) FILTER (WHERE {both} AND {expr}) AS {_q("n__" + name)}'
            for name, expr in null_by_column.items()
        ]
    )
    tally_clause = (",\n  " + tallies) if tallies else ""

    sql = f"""
SELECT
  count(*) FILTER (WHERE c.{anchor} IS NULL)                       AS only_oracle,
  count(*) FILTER (WHERE o.{anchor} IS NULL)                       AS only_candidate,
  count(*) FILTER (WHERE {both} AND NOT ({all_equal}))             AS differing,
  count(*) FILTER (WHERE {row_conflict})                           AS differing_conflict,
  count(*) FILTER (WHERE {row_null_only})                          AS differing_null_only,
  count(*) FILTER (WHERE {both} AND ({all_equal}))                 AS identical,
  count(*) FILTER (WHERE {both} AND ({representable_equal}))       AS identical_representable{tally_clause}
FROM {oracle_ref} o
FULL OUTER JOIN {scan} c ON {join_on}
"""
    row = con.execute(sql).fetchone()
    columns = [d[0] for d in con.description]
    counts = dict(zip(columns, row))

    def _by_column(prefix: str) -> Dict[str, int]:
        """Affected columns only, most-affected first -- the diagnostic payload."""
        return dict(
            sorted(
                (
                    (name, counts[prefix + name])
                    for name in eq_by_column
                    if counts.get(prefix + name)
                ),
                key=lambda kv: (-kv[1], kv[0]),
            )
        )

    columns_conflicting = _by_column("k__")
    columns_candidate_null = _by_column("n__")

    diff: Dict[str, Any] = {
        "key": list(key),
        "classification": "keyed",
        "only_oracle": counts["only_oracle"],
        "only_candidate": counts["only_candidate"],
        "identical": counts["identical"],
        # Identity over the columns the port could ever produce. Equal to
        # `identical` unless a declared-unrepresentable column was confirmed,
        # in which case `identical` is dominated by an all-NULL column and
        # says nothing about the port.
        "identical_representable": counts["identical_representable"],
        "excluded_as_unrepresentable": sorted(representable_only),
        # Total, kept so an older reader still sees the aggregate; the two
        # components below are what the verdict is actually built from.
        "differing": counts["differing"],
        "differing_conflict": counts["differing_conflict"],
        "differing_null_only": counts["differing_null_only"],
        "columns_conflicting": columns_conflicting,
        "columns_candidate_null": columns_candidate_null,
        "columns_differing": dict(
            sorted(
                (
                    (name, columns_conflicting.get(name, 0)
                     + columns_candidate_null.get(name, 0))
                    for name in set(columns_conflicting) | set(columns_candidate_null)
                ),
                key=lambda kv: (-kv[1], kv[0]),
            )
        ),
    }

    if sample_limit > 0:
        diff["samples"] = _keyed_samples(
            con, oracle_ref, scan, key, value_columns, all_equal, join_on,
            anchor, both, sample_limit, row_conflict, row_null_only,
        )

    # Attempted only when there is a conflict to explain: attribution can lower
    # the judge's bar, so it must never run -- and never appear in the artifact
    # -- for a result that has nothing contested about it.
    if counts["differing_conflict"]:
        key_select = ", ".join(
            f"coalesce(o.{_q(k)}, c.{_q(k)}) AS {_q(k)}" for k in key
        )
        pairs = "".join(
            f", o.{_q(c['name'])} AS {_q(c['name'] + '__oracle')}"
            f", c.{_q(c['name'])} AS {_q(c['name'] + '__candidate')}"
            for c in value_columns
        )
        diff["conflict_attribution"] = _attribute_dst_conflicts(
            con,
            cte="",
            from_sql=f"FROM {oracle_ref} o FULL OUTER JOIN {scan} c ON {join_on}",
            row_conflict=row_conflict,
            conflict_by_column=conflict_by_column,
            types_by_column={c["name"]: c["type"] for c in value_columns},
            sample_select=key_select + pairs,
            sample_limit=sample_limit,
        )
    return diff


def _keyed_samples(
    con, oracle_ref, scan, key, value_columns, all_equal, join_on,
    anchor, both, limit, row_conflict, row_null_only,
) -> Dict[str, List[Any]]:
    """A bounded sample of each divergence class, for diagnosis.

    Conflicts and NULL-only rows are sampled separately: they route to
    different places (a fix versus the judge), so a single mixed sample would
    make both harder to read.
    """
    key_select = ", ".join(f"coalesce(o.{_q(k)}, c.{_q(k)}) AS {_q(k)}" for k in key)

    def _rows(where: str, extra_select: str = "") -> List[Dict[str, Any]]:
        sql = f"""
SELECT {key_select}{extra_select}
FROM {oracle_ref} o
FULL OUTER JOIN {scan} c ON {join_on}
WHERE {where}
LIMIT {int(limit)}
"""
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    # For differing rows, show both sides of every value column so the
    # discrepancy is visible without a second round trip.
    pairs = "".join(
        f", o.{_q(c['name'])} AS {_q(c['name'] + '__oracle')}"
        f", c.{_q(c['name'])} AS {_q(c['name'] + '__candidate')}"
        for c in value_columns
    )
    return {
        "only_oracle": _rows(f"c.{anchor} IS NULL"),
        "only_candidate": _rows(f"o.{anchor} IS NULL"),
        "differing_conflict": _rows(row_conflict, pairs),
        "differing_null_only": _rows(row_null_only, pairs),
    }


#: A residual bigger than this is not paired. Pairing costs O(columns) scans of
#: the residual, and a residual this size is a systematic failure whose
#: diagnosis does not turn on which individual rows correspond.
RESIDUAL_PAIRING_CAP = 5_000_000


def _identity_columns(names: Sequence[str]) -> List[str]:
    """Columns that identify a subject, admission, stay or specimen.

    ``LOOP_CONTRACT.md`` requires a key to be *anchored* by at least one of
    these, and a pairing set is a key in everything except uniqueness, so it
    inherits the rule.  Pairing on values alone -- "the rows where
    ``drug = 'Lisinopril'`` and both times are NULL" -- aligns rows that have
    nothing to do with each other, which manufactures precisely the evidence
    the pairing exists to supply.
    """
    return [n for n in names if n == "id" or n.endswith("_id")]


def _residual_pairing(
    con: Any,
    names: Sequence[str],
    sample_limit: int,
    types_by_column: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Decide whether the two residuals are *substitutions* or unmatched rows.

    ``only_oracle`` and ``only_candidate`` cannot answer this, and their
    *equality* answers it even less.  ``EXCEPT ALL`` is multiset difference, so

        |only_oracle| - |only_candidate| == oracle_rows - candidate_rows

    identically.  When the row counts match the two counts are *necessarily*
    equal -- for every port, however wrong.  Reading that equality as "the rows
    are paired, not invented" reads an arithmetic identity as evidence, and no
    amount of care by the reader can extract a fact that is not there.

    So pair them for real.  Find a small set of columns ``D`` such that the two
    residuals are equal as multisets once ``D`` is projected away.  If one
    exists, the residual is "the same rows, differing in ``D``" and ``D`` names
    the columns at fault -- what the keyed diff would have reported had a key
    existed.  If none exists, that failure is itself the finding: the rows are
    genuinely unmatched, and ``only_candidate`` means what it says.

    Expects ``_resid_o`` / ``_resid_c`` to already exist as temp tables.
    """
    n_o = con.execute("SELECT count(*) FROM _resid_o").fetchone()[0]
    n_c = con.execute("SELECT count(*) FROM _resid_c").fetchone()[0]
    if n_o == 0 and n_c == 0:
        return {"attempted": False, "why": "no residual to pair"}
    if max(n_o, n_c) > RESIDUAL_PAIRING_CAP:
        return {
            "attempted": False,
            "why": (
                f"residual of {max(n_o, n_c):,} rows exceeds the "
                f"{RESIDUAL_PAIRING_CAP:,} pairing cap; a divergence this size "
                "is systematic and does not need row-level pairing to diagnose"
            ),
        }

    def _unpaired(stable: Sequence[str]) -> tuple[int, int]:
        sel = ", ".join(_q(n) for n in stable)
        a = con.execute(
            f"SELECT count(*) FROM (SELECT {sel} FROM _resid_o "
            f"EXCEPT ALL SELECT {sel} FROM _resid_c)"
        ).fetchone()[0]
        b = con.execute(
            f"SELECT count(*) FROM (SELECT {sel} FROM _resid_c "
            f"EXCEPT ALL SELECT {sel} FROM _resid_o)"
        ).fetchone()[0]
        return a, b

    # A column whose *marginal* multiset is identical on both sides cannot be
    # what separates the rows, so the diverging columns are exactly those with
    # non-zero drift. Start from all of them and then shrink, rather than
    # searching: the answer is usually the whole drifting set.
    drift: Dict[str, int] = {}
    for name in names:
        q = _q(name)
        drift[name] = con.execute(
            f"SELECT (SELECT count(*) FROM (SELECT {q} FROM _resid_o "
            f"EXCEPT ALL SELECT {q} FROM _resid_c)) + "
            f"(SELECT count(*) FROM (SELECT {q} FROM _resid_c "
            f"EXCEPT ALL SELECT {q} FROM _resid_o))"
        ).fetchone()[0]

    substituted = [n for n in names if drift[n]]
    stable = [n for n in names if n not in set(substituted)]
    result: Dict[str, Any] = {
        "attempted": True,
        "residual_oracle": n_o,
        "residual_candidate": n_c,
        "column_drift": dict(sorted(drift.items(), key=lambda kv: (-kv[1], kv[0]))),
    }

    if not stable:
        result.update(
            paired=0, unpaired_oracle=n_o, unpaired_candidate=n_c,
            pairing_columns=[], substituted_columns=sorted(substituted),
            anchored=False,
            why=("every column differs between the residuals; there is nothing "
                 "left to align rows on, so the residual cannot be shown to be "
                 "substitutions rather than invented and missing rows"),
        )
        return result

    unpaired_o, unpaired_c = _unpaired(stable)

    # Shrink D: a column that drifts but is not *needed* to align the rows
    # belongs in the pairing set, where it strengthens the anchor. Try the
    # least-drifting first, since it is the likeliest passenger.
    if unpaired_o == 0 and unpaired_c == 0:
        for name in sorted(substituted, key=lambda n: (drift[n], n)):
            trial = sorted(stable + [name])
            if _unpaired(trial) == (0, 0):
                stable, substituted = trial, [n for n in substituted if n != name]

    anchors = _identity_columns(stable)
    result.update(
        paired=n_o - unpaired_o,
        unpaired_oracle=unpaired_o,
        unpaired_candidate=unpaired_c,
        pairing_columns=sorted(stable),
        substituted_columns=sorted(substituted),
        anchored=bool(anchors),
        anchor_columns=anchors,
    )
    if unpaired_o or unpaired_c:
        result["why"] = (
            f"{unpaired_o:,} oracle and {unpaired_c:,} candidate residual rows "
            "do not correspond under any small column set; these are genuinely "
            "missing and invented rows, not substitutions"
        )
    elif not anchors:
        result["why"] = (
            "the residual pairs, but on no identity column -- rows were aligned "
            "by value alone, which can pair rows that have nothing to do with "
            "each other. Treat this pairing as unproven"
        )
    if not substituted:
        return result

    result.update(
        _paired_columns(
            con, stable, substituted, sample_limit, types_by_column or {}
        )
    )
    return result


def _paired_columns(
    con: Any,
    stable: Sequence[str],
    substituted: Sequence[str],
    sample_limit: int,
    types_by_column: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Classify the paired residual per column, as the keyed diff would.

    Pairs rows within each stable-column group by position, which is
    well-defined because the two sides agree on that group as a multiset.  Then
    each substituted column reads exactly like a keyed column: candidate NULL
    where the oracle holds a value is a **gap**, anything else is a **conflict**.
    That is the classification ``unavailable_no_key`` was withholding.
    """
    join_on = " AND ".join(f"o.{_q(n)} IS NOT DISTINCT FROM c.{_q(n)}" for n in stable)
    order = ", ".join(_q(n) for n in substituted)
    part = ", ".join(_q(n) for n in stable)
    ranked = (
        f"WITH o AS (SELECT *, row_number() OVER (PARTITION BY {part} "
        f"ORDER BY {order}) AS _rn FROM _resid_o), "
        f"c AS (SELECT *, row_number() OVER (PARTITION BY {part} "
        f"ORDER BY {order}) AS _rn FROM _resid_c)"
    )

    null_sql = {n: _column_candidate_null_sql(n) for n in substituted}
    conflict_sql = {
        n: f"(NOT (o.{_q(n)} IS NOT DISTINCT FROM c.{_q(n)}) AND NOT {null_sql[n]})"
        for n in substituted
    }
    any_conflict = " OR ".join(conflict_sql.values())
    any_null = " OR ".join(null_sql.values())
    tallies = ",\n  ".join(
        [f'count(*) FILTER (WHERE {e}) AS {_q("k__" + n)}' for n, e in conflict_sql.items()]
        + [f'count(*) FILTER (WHERE {e}) AS {_q("n__" + n)}' for n, e in null_sql.items()]
    )
    row = con.execute(
        f"{ranked} SELECT count(*) AS paired, "
        f"count(*) FILTER (WHERE {any_conflict}) AS conflict, "
        f"count(*) FILTER (WHERE NOT ({any_conflict}) AND ({any_null})) AS null_only, "
        f"{tallies} FROM o JOIN c ON {join_on} AND o._rn = c._rn"
    ).fetchone()
    counts = dict(zip([d[0] for d in con.description], row))

    def _by_column(prefix: str) -> Dict[str, int]:
        return dict(
            sorted(
                ((n, counts[prefix + n]) for n in substituted if counts.get(prefix + n)),
                key=lambda kv: (-kv[1], kv[0]),
            )
        )

    out: Dict[str, Any] = {
        "paired_conflict": counts["conflict"],
        "paired_null_only": counts["null_only"],
        "columns_conflicting": _by_column("k__"),
        "columns_candidate_null": _by_column("n__"),
    }
    pairs = "".join(
        f", o.{_q(n)} AS {_q(n + '__oracle')}, c.{_q(n)} AS {_q(n + '__candidate')}"
        for n in substituted
    )
    stable_select = ", ".join("o." + _q(n) for n in stable)
    if sample_limit > 0:
        cur = con.execute(
            f"{ranked} SELECT {stable_select}{pairs} "
            f"FROM o JOIN c ON {join_on} AND o._rn = c._rn LIMIT {int(sample_limit)}"
        )
        cols = [d[0] for d in cur.description]
        out["samples"] = [dict(zip(cols, r)) for r in cur.fetchall()]

    # Same predicate, over the pairing's own alignment rather than a key join --
    # an unkeyed concept whose residual paired is diagnosed like a keyed one, so
    # it earns the same attribution.
    if counts["conflict"]:
        out["conflict_attribution"] = _attribute_dst_conflicts(
            con,
            cte=ranked,
            from_sql=f"FROM o JOIN c ON {join_on} AND o._rn = c._rn",
            row_conflict=f"({any_conflict})",
            conflict_by_column=conflict_sql,
            types_by_column=types_by_column or {},
            sample_select=stable_select + pairs,
            sample_limit=sample_limit,
        )
    return out


def _multiset_diff(
    con: Any,
    oracle_ref: str,
    scan: str,
    columns: Sequence[Dict[str, str]],
    sample_limit: int,
) -> Dict[str, Any]:
    """Full-tuple multiset comparison, for concepts with no unique key.

    Complete as an equivalence check -- ``EXCEPT ALL`` respects duplicate
    multiplicity -- but it names no column, so diagnosis is harder than with a
    keyed diff.

    With no key there is nothing to align rows on, so a row whose only fault is
    a NULL where the oracle holds a value lands in ``only_oracle`` *and*
    ``only_candidate`` simultaneously -- byte-identical, from here, to a row the
    candidate invented.  That is why the two counts alone are not a
    classification, and why their *equality* is not evidence of anything: it is
    forced by equal row counts (see ``_residual_pairing``).

    So the residual is paired explicitly.  When it pairs on an anchored column
    set the classification is recovered and this concept is diagnosed like a
    keyed one; when it does not, the result keeps ``unavailable_no_key`` and the
    judge is told it is reasoning without that evidence.
    """
    names = [c["name"] for c in columns]
    o_proj = ", ".join(_q(n) for n in names)
    # Cast the candidate to the oracle's declared types so EXCEPT ALL does not
    # fail on a merely-cosmetic type difference (Spark long vs DuckDB BIGINT).
    c_proj = ", ".join(f"CAST({_q(c['name'])} AS {c['type']}) AS {_q(c['name'])}" for c in columns)

    con.execute(
        f"CREATE OR REPLACE TEMP TABLE _resid_o AS SELECT {o_proj} FROM {oracle_ref} "
        f"EXCEPT ALL SELECT {c_proj} FROM {scan}"
    )
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE _resid_c AS SELECT {c_proj} FROM {scan} "
        f"EXCEPT ALL SELECT {o_proj} FROM {oracle_ref}"
    )
    only_oracle = con.execute("SELECT count(*) FROM _resid_o").fetchone()[0]
    only_candidate = con.execute("SELECT count(*) FROM _resid_c").fetchone()[0]

    pairing = _residual_pairing(
        con, names, sample_limit, {c["name"]: c["type"] for c in columns}
    )
    paired = (
        pairing.get("attempted")
        and pairing.get("anchored")
        and not pairing.get("unpaired_oracle")
        and not pairing.get("unpaired_candidate")
    )

    diff: Dict[str, Any] = {
        "key": None,
        "classification": "paired_residual" if paired else "unavailable_no_key",
        "only_oracle": only_oracle,
        "only_candidate": only_candidate,
        "residual_pairing": pairing,
        # Undefined unless the residual paired, which supplies the alignment a
        # key would have.
        "differing": None,
        "differing_conflict": None,
        "differing_null_only": None,
        "identical": None,
    }
    if paired:
        # The pairing set aligned every residual row, so `only_oracle` and
        # `only_candidate` are not missing and invented rows at all -- they are
        # the two halves of one substitution, now classified by column.
        oracle_rows = con.execute(f"SELECT count(*) FROM {oracle_ref}").fetchone()[0]
        diff.update(
            differing=pairing["paired"],
            differing_conflict=pairing.get("paired_conflict", 0),
            differing_null_only=pairing.get("paired_null_only", 0),
            columns_conflicting=pairing.get("columns_conflicting", {}),
            columns_candidate_null=pairing.get("columns_candidate_null", {}),
            # Every residual oracle row paired, so the rest reproduced exactly.
            # An unkeyed concept could not state this before, which is why its
            # judges were quoting overlap fractions computed by hand.
            identical=oracle_rows - pairing["paired"],
            only_oracle=0,
            only_candidate=0,
            multiset_only_oracle=only_oracle,
            multiset_only_candidate=only_candidate,
        )
        # Lifted out of the pairing so the classifier reads it from one place
        # regardless of whether the concept has a key.
        if pairing.get("conflict_attribution"):
            diff["conflict_attribution"] = pairing["conflict_attribution"]
    if sample_limit > 0:
        def _sample(table: str) -> List[Dict[str, Any]]:
            cur = con.execute(f"SELECT * FROM {table} LIMIT {int(sample_limit)}")
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

        if paired:
            # Showing these as `only_oracle` / `only_candidate` would contradict
            # the counts, which the pairing has just established are zero. They
            # are two views of one set of substituted rows, and the paired
            # sample already shows both sides of each on one line.
            diff["samples"] = {"substitutions": pairing.get("samples", [])}
        else:
            diff["samples"] = {
                "only_oracle": _sample("_resid_o"),
                "only_candidate": _sample("_resid_c"),
            }
    return diff


def compare_full(
    concept: str,
    manifest_path: str | Path,
    oracle_db: str | Path,
    candidate_path: str | Path,
    *,
    schema: str = DERIVED_SCHEMA,
    rtol: float = DEFAULT_RTOL,
    atol: float = DEFAULT_ATOL,
    sample_limit: int = DEFAULT_SAMPLE_LIMIT,
    unrepresentable: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Full-data correctness gate: row count, schema, and the keyed diff.

    *unrepresentable* is the parsed ``unrepresentable.json`` declaration, if the
    attempt carries one: column name -> justification for columns the port
    claims MIMIC-on-FHIR cannot represent at all. It is verified, not trusted.
    """
    import duckdb

    entry = load_manifest_entry(manifest_path, concept)
    oracle_db = Path(oracle_db)
    if not oracle_db.is_file():
        raise FileNotFoundError(f"Oracle not found: {oracle_db}")

    result: Dict[str, Any] = {
        "format_version": "2.0",
        "mode": "full",
        "concept": concept,
        "dataset": "full",
        "candidate": str(candidate_path),
        "oracle": {
            "path": str(oracle_db),
            "table": f"{schema}.{concept}",
            "manifest_row_count": entry["row_count"],
            "manifest_content_hash": entry.get("content_hash"),
        },
        "tolerances": {
            "row_count": "none (exact)",
            "relative": rtol,
            "absolute": atol,
            "timestamp_seconds": TIMESTAMP_TOL_SECONDS,
        },
    }

    con = duckdb.connect(":memory:")
    try:
        # The oracle is read-only: a comparison must never be able to mutate
        # the ground truth it is comparing against.
        con.execute(f"ATTACH {_lit(str(oracle_db))} AS oracle (READ_ONLY)")
        oracle_ref = f"oracle.{schema}.{_q(concept)}"
        scan = scan_expression(candidate_path)

        try:
            actual = _candidate_columns(con, scan)
            candidate_rows = con.execute(f"SELECT count(*) FROM {scan}").fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            result["executed"] = False
            result["error"] = str(exc)
            result["match"] = False
            result["verdict"] = "mismatch"
            return result

        result["executed"] = True

        oracle_rows = con.execute(f"SELECT count(*) FROM {oracle_ref}").fetchone()[0]
        result["row_count"] = {
            "oracle": oracle_rows,
            "candidate": candidate_rows,
            "delta": candidate_rows - oracle_rows,
            "match": oracle_rows == candidate_rows,
            # Reported, never gated. MIMIC-on-FHIR does not carry everything
            # relational MIMIC-IV carries, so a faithful port can legitimately
            # return fewer rows. Which *kind* of difference it is decides the
            # verdict, and that lives in `divergence` below.
            "gated": False,
        }
        if oracle_rows != entry["row_count"]:
            result.setdefault("warnings", []).append(
                f"Oracle table has {oracle_rows} rows but the manifest records "
                f"{entry['row_count']}: the manifest is stale relative to this oracle."
            )

        result["schema"] = _compare_schemas(entry["columns"], actual)

        # A keyed join across mismatched columns yields noise, not a diagnosis.
        if not result["schema"]["match"]:
            result["diff"] = None
            result["diff_skipped"] = "schema mismatch: fix columns before diffing rows"
            result["match"] = False
            result["verdict"] = "mismatch"
            return result

        # Verified only after the schema matches: a declaration about a column
        # that is not there yet would report a confusing second failure on top
        # of the schema one.
        if unrepresentable:
            result["unrepresentable"] = _verify_unrepresentable(
                unrepresentable, entry, con, scan
            )

        confirmed_unrepresentable = frozenset(
            (result.get("unrepresentable") or {}).get("confirmed") or {}
        )

        key = entry.get("key")
        columns = entry["columns"]
        if key:
            value_columns = [c for c in columns if c["name"] not in set(key)]
            result["comparison"] = "keyed_join"
            result["diff"] = _keyed_diff(
                con, oracle_ref, scan, key, value_columns, rtol, atol, sample_limit,
                representable_only=confirmed_unrepresentable,
            )
        else:
            result["comparison"] = "full_tuple_multiset"
            result["diff"] = _multiset_diff(con, oracle_ref, scan, columns, sample_limit)

        result["divergence"] = _classify_divergence(
            result["diff"], oracle_rows, result.get("unrepresentable")
        )
        result["verdict"] = result["divergence"]["verdict"]
        result["match"] = result["verdict"] == "match"
        result["diagnostics"] = _diagnostics(result)
        return result
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Divergence classification -- what the verdict is actually built from
# ---------------------------------------------------------------------------

#: Divergence classes a MIMIC-on-FHIR coverage gap can produce. An accept here
#: needs a named absent element.
_GAP_CLASSES = {
    "only_oracle": (
        "oracle rows the candidate never produced; this is the shape a "
        "legitimate MIMIC-on-FHIR coverage gap takes"
    ),
    "differing_null_only": (
        "matched rows where the candidate is NULL and the oracle holds a "
        "value; consistent with the FHIR element for that column not existing"
    ),
}

#: Divergence classes a coverage gap CANNOT produce -- but upstream ETL
#: transformation can, and so can a port bug, and the two are indistinguishable
#: from the data alone. These used to hard-fail. They no longer do: hard-failing
#: them fails faithful ports of concepts whose values MIMIC-on-FHIR rewrites
#: (birthDate synthesis, TIMESTAMPTZ normalisation). They reach the judge at a
#: raised bar instead -- see ``_CONTESTED_BAR``.
_CONTESTED_CLASSES = {
    "only_candidate": (
        "rows the candidate produced that the oracle does not have. Usually "
        "join fan-out or a filter the oracle SQL applies and the port does "
        "not; a coverage gap cannot cause it"
    ),
    "differing_conflict": (
        "matched rows where both sides hold a value and the values "
        "disagree, or the candidate holds a value where the oracle holds NULL. "
        "Either a port bug or upstream ETL transformation loss (MIMIC-on-FHIR "
        "carrying a *different* value, not a missing one) -- indistinguishable "
        "from the data alone"
    ),
}

#: Divergence classes that are machine-provable contradictions. Nothing is
#: weighed and the judge is not called: the port contradicted itself, or the
#: result is not comparable at all.
_UNRESOLVABLE_CLASSES = {
    "false_unrepresentable_declaration": (
        "the port declared a column unrepresentable and then emitted values "
        "for it; the claim and the data contradict each other"
    ),
}

#: What an ``accept`` must establish, per tier. Written into the artifact so the
#: judge argues to the standard the result actually requires rather than to the
#: one it remembers.
_GAP_BAR = (
    "Cite the FHIR element or path that does not exist in the MIMIC-on-FHIR "
    "IG, show it explains the magnitude and shape of the divergence, and "
    "confirm every defensible mapping was tried."
)
_CONTESTED_BAR = (
    "A conflict is not gap-shaped, so an absent element does not explain it. "
    "An accept must cite the upstream mimic-fhir ETL statement (file and line) "
    "that writes a different value than relational MIMIC-IV holds, and show "
    "the oracle value is not recoverable from what FHIR does carry by ANY "
    "query -- not merely that this port did not recover it. Absent that "
    "citation the answer is `bug`. State the affected fraction: a conflict "
    "concentrated in a few rows with an identified ETL cause is a different "
    "claim from one spread across the table."
)

#: What the judge must still establish once the comparator has replayed the
#: upstream cast over the whole conflict set. Deliberately explicit about the
#: two things the replay does NOT prove, because this is the tier that could
#: otherwise become a rubber stamp.
_ATTRIBUTED_BAR = (
    "The only value conflict present has been machine-attributed to an upstream "
    "mimic-fhir transformation: the comparator replayed the ETL's TIMESTAMPTZ "
    "cast over EVERY conflicting row -- not a sample -- and the candidate value "
    "is what that cast produces from the oracle value. So the arithmetic half "
    "of the `contested` bar is already discharged: the oracle value was "
    "overwritten before the FHIR resource was written and no query can recover "
    "it. Do NOT ask the port to fix it, and do NOT ask for the diagnostician's "
    "citation -- see `divergence.attributed[].citations`.\n"
    "Two things the replay does NOT establish, and they are yours:\n"
    "(1) PROVENANCE. The citations are the known sites of that cast, not a "
    "per-column proof. Confirm one of them writes the FHIR element this "
    "column is actually sourced from; if none does, the replay is a "
    "coincidence and the answer is `bug`.\n"
    "(2) SHAPE. DST-gap wall times are rare by construction -- one hour per "
    "year. A large attributed fraction is evidence AGAINST the attribution, "
    "not for it: state the fraction, and answer `bug` if it is not consistent "
    "with that rarity.\n"
    "Everything else the two bars require of you is unchanged: an accept is "
    "still an explicit ruling, and the gap must still be the best the data "
    "allows."
)

#: Appended to the gap bar when a conflict was attributed but gap-shaped
#: divergence remains. The gap is what the judge is deciding; the attribution is
#: context it must not silently absorb into that decision.
_ATTRIBUTED_ADDENDUM = (
    "A value conflict is also present but has been machine-attributed to an "
    "upstream transformation (see `divergence.attributed`), which is why this "
    "result is gap-shaped rather than contested. Rule on the gap on its own "
    "merits, and check the attribution's provenance and fraction as "
    "`divergence.attributed[].judge_must_confirm` states."
)

#: Handed to the judge on every attributed class, so the obligation travels with
#: the finding rather than only with the bar.
_ATTRIBUTED_CONFIRM = (
    "Confirm (a) that one of the cited mimic-fhir statements writes the FHIR "
    "element this column is sourced from, and (b) that the attributed fraction "
    "is consistent with DST-gap rarity. Either failing makes this `bug`."
)


def _classify_divergence(
    diff: Dict[str, Any],
    oracle_rows: int,
    unrepresentable: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Decide ``match`` / ``mismatch`` / ``review`` from the classified diff.

    Row count never appears here.  What matters is the *shape* of the
    divergence, and which of the three things that shape can mean.

    Only a machine-provable contradiction is a ``mismatch``: the port
    contradicted its own declaration, or the result is not comparable at all.
    Everything else the judge decides, at one of two bars.  Gap-shaped
    divergence needs a named absent element.  A conflict needs more, because an
    absence does not explain a wrong value -- it needs the upstream ETL
    statement that rewrote it.  Both reach the judge, because a conflict is
    equally consistent with a port bug and with transformation loss, and the
    comparator cannot see which.

    A verified ``unrepresentable`` declaration is **evidence, not a verdict**.
    It never turns ``review`` into ``match`` -- the judge still rules, and
    still has to accept the gap explicitly. What it does is attach the port's
    stated reason to the divergence it explains, and hard-fail a declaration
    the data contradicts.
    """
    unkeyed = diff.get("classification") == "unavailable_no_key"

    def _present(names: Dict[str, str]) -> List[Dict[str, Any]]:
        out = []
        for name, why in names.items():
            count = diff.get(name)
            if count:
                out.append({"class": name, "count": count, "why": why})
        return out

    gap_shaped = _present(_GAP_CLASSES)
    contested = _present(_CONTESTED_CLASSES)
    unresolvable: List[Dict[str, Any]] = []

    notes: List[str] = []

    # A conflict class the comparator proved is an upstream transformation moves
    # out of `contested` and into `attributed`. It stays a divergence and the
    # judge still rules on it -- only the bar changes, and only because the
    # comparator has already met the part of that bar it can meet by machine.
    attributed: List[Dict[str, Any]] = []
    attribution = diff.get("conflict_attribution") or {}
    if attribution.get("complete"):
        remaining: List[Dict[str, Any]] = []
        for item in contested:
            if item["class"] != "differing_conflict":
                remaining.append(item)
                continue
            item = dict(item)
            item.update(
                attributed_to=attribution["cause"],
                attributed_rows=attribution["attributed_rows"],
                proof=attribution["operation"],
                citations=attribution["citations"],
                columns=attribution.get("columns") or {},
                judge_must_confirm=_ATTRIBUTED_CONFIRM,
            )
            attributed.append(item)
        contested = remaining
    elif attribution.get("attempted") and attribution.get("attributed_rows"):
        # Partial attribution changes nothing about the tier -- the unexplained
        # rows decide it -- but the diagnostician should not spend a run
        # re-deriving the part that is already proved.
        notes.append(
            f"{attribution['attributed_rows']:,} of "
            f"{attribution['conflict_rows']:,} conflicting rows replay the "
            f"upstream {attribution['cause']}; {attribution['residual_rows']:,} "
            "do not and are unexplained. The tier stays `contested` on those "
            "residual rows: diagnose them, not the attributed ones."
        )
    elif attribution.get("attempted") is False and attribution.get("why"):
        notes.append(f"upstream conflict attribution not attempted: {attribution['why']}")
    pairing = diff.get("residual_pairing") or {}
    if diff.get("classification") == "paired_residual":
        # The residual paired on an anchored column set, so the classes below
        # were computed the same way a keyed concept's are. Say so, because the
        # tier now rests on that pairing rather than on the raw multiset counts.
        notes.append(
            "No unique key, but the residual paired 1:1 on "
            f"{', '.join(pairing.get('pairing_columns') or [])} "
            f"(anchored by {', '.join(pairing.get('anchor_columns') or [])}), "
            f"differing only in {', '.join(pairing.get('substituted_columns') or [])}. "
            f"The {diff.get('multiset_only_candidate', 0):,} multiset "
            "`only_candidate` rows are therefore the candidate half of those "
            "substitutions, not invented rows, and the classes below are "
            "classified per column as for a keyed concept."
        )
    elif unkeyed:
        # Without a key, `only_candidate` is ambiguous in a third way: a
        # NULL-for-value divergence shows up identically to an invented row.
        for item in contested:
            if item["class"] == "only_candidate":
                item["why"] = (
                    "rows in the candidate that are not in the oracle -- but "
                    "this concept has no unique key, so a row whose only fault "
                    "is a NULL appears here too. Invented rows and NULL "
                    "divergence are INDISTINGUISHABLE for this concept; treat "
                    "as a bug unless the evidence positively shows otherwise"
                )
        notes.append(
            "No unique key for this concept, and the residual did not pair: "
            "divergence classes cannot be separated. The judge is reasoning "
            "with strictly less evidence than a keyed concept would provide."
        )
        if pairing.get("why"):
            notes.append(f"residual pairing: {pairing['why']}")
        # The one inference that is *never* available here, stated explicitly
        # because it looks like evidence and is not.
        if diff.get("only_oracle") and diff["only_oracle"] == diff.get("only_candidate"):
            notes.append(
                "`only_oracle` and `only_candidate` are both "
                f"{diff['only_oracle']:,}. EXCEPT ALL is multiset difference, so "
                "their difference equals the row-count difference identically: "
                "with equal row counts they are equal for EVERY candidate, "
                "however wrong. This equality is NOT evidence that the rows are "
                "paired -- the pairing above tried to establish that and failed."
            )

    # A declaration the data contradicts is the one thing here that needs no
    # judgement: the port claimed a column has no FHIR representation and then
    # produced values for it. That is the estimate-instead-of-NULL failure the
    # declaration exists to catch, and the claim refutes itself.
    explained: Dict[str, str] = {}
    if unrepresentable:
        explained = unrepresentable.get("confirmed") or {}
        for violation in unrepresentable.get("violations") or []:
            unresolvable.append({
                "class": "false_unrepresentable_declaration",
                "count": violation.get("non_null_rows", 1),
                "why": (
                    f"column {violation['column']!r} {violation['reason']}"
                ),
            })
        if explained:
            for item in gap_shaped:
                if item["class"] == "differing_null_only":
                    item["declared_unrepresentable"] = explained
        undeclared = unrepresentable.get("undeclared_fully_null_columns") or []
        if undeclared:
            notes.append(
                "Columns that are 100% NULL in the candidate but carry no "
                f"declaration: {', '.join(undeclared)}. Either declare them in "
                f"{UNREPRESENTABLE_FILENAME} with a justification, or explain "
                "why they are empty."
            )

    if unresolvable:
        verdict, tier, bar = "mismatch", "unresolvable", None
    elif contested:
        verdict, tier, bar = "review", "contested", _CONTESTED_BAR
    elif gap_shaped:
        verdict, tier, bar = "review", "gap_shaped", _GAP_BAR
        if attributed:
            bar = _GAP_BAR + "\n" + _ATTRIBUTED_ADDENDUM
    elif attributed:
        # Still `review`, never `match`: the values genuinely differ from the
        # oracle, and who gets to accept that is the judge. Attribution buys a
        # lower bar and a skipped diagnosis, not a pass.
        verdict, tier, bar = "review", "attributed", _ATTRIBUTED_BAR
    else:
        verdict, tier, bar = "match", "none", None

    if attributed:
        notes.append(
            f"{attribution['attributed_rows']:,} of "
            f"{attribution['conflict_rows']:,} conflicting rows -- all of them "
            f"-- replay the upstream {attribution['cause']} exactly, over "
            f"column(s) {', '.join(attribution.get('columns') or {}) or 'n/a'}. "
            "`differing_conflict` moved from `contested` to `attributed`; a "
            "diagnosis of this class would only re-derive the replay, so the "
            "diagnostician can be skipped. The judge cannot: it still has to "
            "confirm provenance and fraction, and still has to rule."
        )

    reproduced = diff.get("identical")
    representable = diff.get("identical_representable")
    excluded = diff.get("excluded_as_unrepresentable") or []

    def _fraction(n: Optional[int]) -> Optional[float]:
        return round(n / oracle_rows, 6) if n is not None and oracle_rows else None

    result: Dict[str, Any] = {
        "verdict": verdict,
        "tier": tier,
        "classification": diff.get("classification"),
        # `blocking` retained as the union of everything that is not gap-shaped,
        # so a reader that keys off it still sees the serious classes -- but it
        # is no longer what decides the verdict. `tier` is.
        "blocking": unresolvable + contested,
        "unresolvable": unresolvable,
        "contested": contested,
        "gap_shaped": gap_shaped,
        # Conflict classes the comparator proved are upstream transformation.
        # Reviewable, never blocking, never a `match`.
        "attributed": attributed,
        # Counts and provenance only -- the sample rows stay in
        # `diff.conflict_attribution`, so the artifact carries them once.
        "conflict_attribution": (
            {k: v for k, v in attribution.items() if k != "samples"}
            if attribution else None
        ),
        # Union of everything the judge rules on, in bar order (highest first).
        "reviewable": contested + gap_shaped + attributed,
        "judge_required": verdict == "review",
        # The one stage attribution is allowed to skip. Written explicitly so
        # the orchestrator reads a decision rather than inferring one from a
        # tier name it may not recognise.
        "diagnostician_required": verdict == "mismatch" or bool(contested),
        "judge_bar": bar,
        "oracle_rows": oracle_rows,
        "identical_rows": reproduced,
        "identical_fraction": _fraction(reproduced),
        "notes": notes,
        "declared_unrepresentable": explained,
        "policy": (
            "Row count is not a hard gate. `mismatch` is reserved for "
            "machine-provable contradictions (schema, execution, a declaration "
            "the data refutes) and the judge is not called. Everything else is "
            "`review`: tier `gap_shaped` needs a named absent FHIR element; "
            "tier `contested` carries a value conflict, which an absence "
            "cannot explain, and needs the upstream ETL statement that "
            "rewrote the value; tier `attributed` carries a conflict the "
            "comparator has already replayed to an upstream ETL cast over "
            "every conflicting row, so the judge confirms provenance and "
            "fraction rather than re-deriving the cause. A conflict is NOT "
            "presumed to be a bug and is NOT presumed to be intrinsic -- the "
            "judge decides which, and the judge is called on EVERY `review` "
            "including `attributed`."
        ),
    }
    if excluded:
        # Reported alongside, never instead of: `identical_fraction` is the
        # honest total, this is the number that is about the port.
        result["identical_representable_rows"] = representable
        result["representable_fraction"] = _fraction(representable)
        result["representable_excludes"] = excluded
    return result


def _diagnostics(result: Dict[str, Any]) -> List[str]:
    """Human-readable summary lines, grouped by what each class means.

    Ordered by how hard the class is to clear, worst first: the reader's next
    action is decided by the most serious thing present.
    """
    out: List[str] = []
    rc = result.get("row_count", {})
    if rc and not rc.get("match"):
        out.append(
            f"row count (not gated): oracle {rc['oracle']:,} vs candidate "
            f"{rc['candidate']:,} (delta {rc['delta']:+,})"
        )

    diff = result.get("diff") or {}
    divergence = result.get("divergence") or {}
    oracle_rows = divergence.get("oracle_rows") or 0

    def _share(n: int) -> str:
        return f" ({n / oracle_rows:.3%} of oracle rows)" if oracle_rows else ""

    pairing = diff.get("residual_pairing") or {}
    if pairing.get("attempted"):
        if diff.get("classification") == "paired_residual":
            out.append(
                f"RESIDUAL PAIRED — {pairing['paired']:,} rows matched 1:1 on "
                f"({', '.join(pairing['pairing_columns'])}), differing only in "
                f"({', '.join(pairing['substituted_columns'])}). The multiset "
                f"`only_oracle`/`only_candidate` counts of "
                f"{diff.get('multiset_only_oracle', 0):,} are the two halves of "
                "these substitutions; they are classified per column below."
            )
        else:
            out.append(
                f"RESIDUAL DID NOT PAIR — {pairing.get('unpaired_oracle', 0):,} "
                f"oracle and {pairing.get('unpaired_candidate', 0):,} candidate "
                "residual rows do not correspond. Their counts being equal "
                "proves nothing: it follows from the row counts being equal."
            )

    if divergence.get("unresolvable"):
        out.append("UNRESOLVABLE — the port contradicts itself; the judge is not called:")
        for item in divergence["unresolvable"]:
            out.append(f"  {item['count']:,} × {item['class']} — {item['why']}")

    if divergence.get("contested"):
        out.append(
            "CONTESTED — a value conflict. Either a port bug or upstream ETL "
            "transformation loss; the data cannot tell you which:"
        )
        for item in divergence["contested"]:
            out.append(
                f"  {item['count']:,} × {item['class']}{_share(item['count'])} "
                f"— {item['why']}"
            )
        for column, n in (diff.get("columns_conflicting") or {}).items():
            out.append(f"    column {column!r} conflicts on {n:,} row(s){_share(n)}")
        out.append(f"  bar for an accept: {_CONTESTED_BAR}")

    if divergence.get("attributed"):
        attribution = diff.get("conflict_attribution") or {}
        out.append(
            "ATTRIBUTED — a value conflict the comparator replayed to an "
            "upstream mimic-fhir transformation over every conflicting row. "
            "No port can invert it, so there is nothing to diagnose; the judge "
            "still rules:"
        )
        for item in divergence["attributed"]:
            out.append(
                f"  {item['count']:,} × {item['class']}{_share(item['count'])} "
                f"— all {item['attributed_rows']:,} replay {item['attributed_to']}"
            )
            for column, n in (item.get("columns") or {}).items():
                out.append(f"    column {column!r}: {n:,} row(s) attributed")
            out.append(f"    citations: {', '.join(item.get('citations') or [])}")
        for sample in (attribution.get("samples") or [])[:1]:
            out.append(f"    example row: {sample}")
        out.append(
            "  the judge must still confirm: "
            f"{divergence['attributed'][0].get('judge_must_confirm', '')}"
        )

    if divergence.get("gap_shaped"):
        out.append("GAP-SHAPED — consistent with a MIMIC-on-FHIR coverage gap:")
        for item in divergence["gap_shaped"]:
            out.append(f"  {item['count']:,} × {item['class']} — {item['why']}")
        declared = divergence.get("declared_unrepresentable") or {}
        for column, n in (diff.get("columns_candidate_null") or {}).items():
            suffix = " [declared unrepresentable]" if column in declared else ""
            out.append(
                f"    column {column!r} is NULL in the candidate on {n:,} row(s){suffix}"
            )
        for column, justification in declared.items():
            out.append(f"    declared {column!r}: {justification}")

    fraction = divergence.get("identical_fraction")
    if fraction is not None:
        out.append(
            f"{divergence['identical_rows']:,} of {divergence['oracle_rows']:,} "
            f"oracle rows reproduced identically ({fraction:.2%})"
        )
    rep_fraction = divergence.get("representable_fraction")
    if rep_fraction is not None:
        excludes = ", ".join(divergence.get("representable_excludes") or [])
        out.append(
            f"{divergence['identical_representable_rows']:,} of "
            f"{divergence['oracle_rows']:,} identical on the representable "
            f"columns ({rep_fraction:.2%}), excluding the declared-and-confirmed "
            f"all-NULL column(s): {excludes}"
        )
    for note in divergence.get("notes") or []:
        out.append(f"note: {note}")
    return out


# ---------------------------------------------------------------------------
# Artifact writing
# ---------------------------------------------------------------------------


def _json_default(value: Any) -> Any:
    """Serialise DuckDB scalars (datetime, Decimal, ...) that JSON cannot."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def write_comparison(result: Dict[str, Any], output_path: str | Path) -> Path:
    """Write the comparison artifact write-once, via a temp file + rename."""
    output_path = Path(output_path).resolve()
    if output_path.exists():
        raise FileExistsError(
            f"Comparison artifact already exists (write-once): {output_path}"
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    try:
        tmp_path.write_text(
            json.dumps(result, indent=2, sort_keys=True, default=_json_default),
            encoding="utf-8",
        )
        tmp_path.replace(output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# Exit codes: 0 pass, 1 fail, 2 neither.
#
# 2 covers both `unsure` (demo, 0 rows) and `review` (full, any tier).
# Neither is a pass or a failure, and collapsing either onto 1 would let a
# caller's `if rc:` turn "the judge must look at this" into "this port is
# wrong" -- which is exactly the error a contested tier is most likely to
# provoke, since it reads as serious.
EXIT_PASS = 0
EXIT_FAIL = 1
EXIT_UNSURE = 2


def report_verdict(result: Dict[str, Any]) -> int:
    """Log a comparison result and return its exit code.

    Shared by both entry points on purpose. This logic previously existed twice
    -- here and in ``mimic_utils.__main__`` -- and the copy drifted: it never
    grew the ``review`` branch, so `mimic_utils compare-port-results full`
    returned ``EXIT_FAIL`` for every ``review``, turning "the judge must look at
    this" into "this port is wrong" for exactly the verdict the exit-code
    comment above warns about.
    """
    verdict = result.get("verdict")
    if verdict in ("match", "shape_ok"):
        logging.info("Comparison: %s", str(verdict).upper())
        return EXIT_PASS
    if verdict == "unsure":
        logging.warning("Comparison: UNSURE — %s", result.get("note", ""))
        return EXIT_UNSURE

    if verdict == "review":
        tier = (result.get("divergence") or {}).get("tier")
        logging.warning(
            "Comparison: REVIEW (tier=%s) — the equivalence judge decides. "
            "This is NOT a failure.%s",
            tier,
            (
                " A value conflict is present: an accept must cite the upstream "
                "ETL statement that rewrote the value, not merely an absence."
                if tier == "contested" else
                " The value conflict was replayed to a known upstream ETL cast "
                "over every conflicting row; no diagnosis is needed, but the "
                "judge still rules."
                if tier == "attributed" else ""
            ),
        )
    else:
        logging.warning("Comparison: %s", str(verdict).upper())

    for line in result.get("diagnostics", []) or []:
        logging.warning("  %s", line)
    if result.get("error"):
        logging.warning("  error: %s", result["error"])
    schema = result.get("schema") or {}
    for field in ("missing_columns", "extra_columns", "incompatible_types"):
        if schema.get(field):
            logging.warning("  %s: %s", field, schema[field])
    return EXIT_UNSURE if verdict == "review" else EXIT_FAIL


def compare_port_results_cli(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="compare-port-results",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "mode",
        choices=("shape", "full"),
        help="shape = demo gate (columns/types only); full = correctness gate",
    )
    ap.add_argument("--concept", required=True)
    ap.add_argument(
        "--manifest",
        required=True,
        help="oracle manifest JSON (mimic-iv/concepts_fhir/oracle/oracle_manifest.full.json)",
    )
    ap.add_argument(
        "--candidate", required=True, help="candidate result (.parquet / .ndjson / .csv)"
    )
    ap.add_argument("--output", required=True, help="comparison JSON (must not exist)")
    ap.add_argument("--oracle", help="oracle DuckDB file (required for --mode full)")
    ap.add_argument("--schema", default=DERIVED_SCHEMA)
    ap.add_argument("--rtol", type=float, default=DEFAULT_RTOL)
    ap.add_argument("--atol", type=float, default=DEFAULT_ATOL)
    ap.add_argument("--sample-limit", type=int, default=DEFAULT_SAMPLE_LIMIT)
    ap.add_argument(
        "--unrepresentable",
        help=(
            f"attempt's {UNREPRESENTABLE_FILENAME}: columns MIMIC-on-FHIR cannot "
            "represent at all, each with a justification. Verified against the "
            "candidate, never trusted. Mode 'full' only."
        ),
    )
    args = ap.parse_args(argv)

    try:
        declared = (
            load_unrepresentable(args.unrepresentable) if args.unrepresentable else None
        )
        if args.mode == "shape":
            if declared:
                ap.error("--unrepresentable applies to mode 'full' only")
            result = compare_shape(args.concept, args.manifest, args.candidate)
        else:
            if not args.oracle:
                ap.error("--oracle is required for mode 'full'")
            result = compare_full(
                args.concept,
                args.manifest,
                args.oracle,
                args.candidate,
                schema=args.schema,
                rtol=args.rtol,
                atol=args.atol,
                sample_limit=args.sample_limit,
                unrepresentable=declared,
            )
    except Exception as exc:  # noqa: BLE001
        logging.error("compare-port-results failed: %s", exc)
        return EXIT_FAIL

    out = write_comparison(result, args.output)
    logging.info("Comparison artifact written: %s", out)
    return report_verdict(result)


if __name__ == "__main__":
    sys.exit(compare_port_results_cli())
