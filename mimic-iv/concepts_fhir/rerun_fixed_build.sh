#!/usr/bin/env bash
#
# Re-measure the ported concepts against the rebuilt MIMIC-on-FHIR warehouse.
#
# Three upstream data defects were fixed on 2026-08-21 and both warehouses were
# rebuilt on 2026-08-24, so almost every recorded verdict was earned against
# data that no longer exists.  This drives the reruns: `mimic_utils goal-run`
# reopens each concept, starts a real orchestrator session on it, and keeps that
# session going until it reports a terminal state -- k concepts at a time.
#
# TODO_upstream_fix_rerun.md is the plan; this is the invocation.  Two modes:
#
#   ./rerun_fixed_build.sh                 # the 49 replays (SQL carried forward)
#   ./rerun_fixed_build.sh --reimplement   # the 3 that need re-authoring
#
# and one for picking a pool back up:
#
#   ./rerun_fixed_build.sh --continue      # whatever the ledger says is unfinished
#
# Usage:
#   ./rerun_fixed_build.sh [-k N] [--wave N] [--dry-run] [--check-only]
#                          [--reimplement] [--continue] [-- <extra goal-run args>]
#
set -euo pipefail

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd -- "$HERE/../.." && pwd)
WAVE_DIR="$HERE/replay"

# One local Spark at a time.  Every worker's `run-demo` takes this flock in
# turn, and so does a /goal you run by hand in another terminal -- but only if
# it is the same path, so an existing export wins.
export MIMIC_SPARK_LOCK="${MIMIC_SPARK_LOCK:-$HOME/.mimic-spark.lock}"

# Recorded on every reopen AND read back to the session by `mimic_utils resume`,
# which is the only channel there is: `/goal` takes the bare concept stem and
# rejects prose beside it.  So this is written for the agent, not for the log.
#
# It names two of the three fixes on purpose.  The third moved categorical
# chartevents text into a new element, and no replayed concept may act on it --
# its SQL is carried forward byte-identical.  Naming a newly served element to a
# session that is forbidden from re-authoring is an invitation to try.
REPLAY_REASON="The MIMIC-on-FHIR warehouse was rebuilt on 2026-08-24 after two upstream data defects were fixed: FHIR resources are now generated under UTC, so wall-clock timestamps are no longer shifted an hour across the spring-forward boundary, and Patient.birthDate is now derived from the anchor year and age rather than from the first transfer. This port was carried forward byte-identical to re-measure it against the corrected data -- do not re-author it. Expect previously accepted divergences to have shrunk or gone; if an hour-wide shift still appears, treat it as a finding and establish why the correction did not reach that path rather than accepting it as an upstream artifact."

# The re-implements were already reopened by hand with their own itemid-level
# reasons (TODO_upstream_fix_rerun.md section 5), so this only has to say what
# the session is walking into.
REIMPLEMENT_REASON="The MIMIC-on-FHIR warehouse was rebuilt on 2026-08-24 and now carries the categorical text of a chartevents measurement in Observation.component[].valueString, coded the same way as Observation.code, alongside the numeric value it used to replace. The unrepresentability this concept declared rests on that text being absent and is therefore no longer true. Re-probe the element, select it, and remove the declaration and the NULL-propagation logic built on top of it."

# Completed before `validate-demo` enforced the resource-key lint, and neither
# emits patient_key (both have encounter_key only).  A byte-identical replay is
# refused at the demo gate -- after the reopen has already been spent -- so they
# need a session that adds the key.  Found by the preflight, not by reading:
# `replay --check` lints the SQL it would carry.
RELINT_CONCEPTS=(milrinone creatinine_baseline)
RELINT_REASON="This port was completed before the resource-key lint that validate-demo now enforces, and it does not emit patient_key, so it cannot be carried forward unchanged. Add patient_key -- taken verbatim and uncast from the Patient view, or from a reference to it -- and change nothing else about the logic. The warehouse was rebuilt on 2026-08-24 after two upstream data defects were fixed: FHIR resources are now generated under UTC, so wall-clock timestamps are no longer shifted an hour across the spring-forward boundary, and Patient.birthDate is now derived from the anchor year and age rather than from the first transfer, so expect previously accepted divergences to have shrunk or gone."

#: Not replayable: their SQL must change, so they get a full loop.  Order
#: matters only in that first_day_gcs depends on gcs -- goal-run enforces it.
REIMPLEMENT_CONCEPTS=(gcs ventilator_setting first_day_gcs)

PARALLEL=6
WAVE=""
DRY_RUN=0
CHECK_ONLY=0
RELINT=0
REIMPLEMENT=0
CONTINUE=0
EXTRA=()

die() { printf '%s\n' "$*" >&2; exit 2; }

usage() {
    # The header comment, up to the first line that is not one -- so editing the
    # header cannot leave the help text truncated or trailing into the code.
    awk 'NR>1 && /^#/ { sub(/^# ?/, ""); print; next } NR>1 { exit }' \
        "${BASH_SOURCE[0]}"
    exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -k|--parallel)  PARALLEL="${2:?-k needs a number}"; shift 2 ;;
        --wave)         WAVE="${2:?--wave needs a number}"; shift 2 ;;
        --dry-run)      DRY_RUN=1; shift ;;
        --check-only)   CHECK_ONLY=1; shift ;;
        --relint)       RELINT=1; shift ;;
        --reimplement)  REIMPLEMENT=1; shift ;;
        --continue)     CONTINUE=1; shift ;;
        -h|--help)      usage 0 ;;
        --)             shift; EXTRA=("$@"); break ;;
        *)              die "Unknown argument: $1 (try --help)" ;;
    esac
done

DRY=()
((DRY_RUN)) && DRY=(--dry-run)

cd "$REPO_ROOT"

((RELINT + REIMPLEMENT + CONTINUE <= 1)) || die "--relint, --reimplement and --continue are separate runs"

# --------------------------------------------------------------------------- #
# pick the pool back up
# --------------------------------------------------------------------------- #

# A pool that stopped short leaves its own worklist behind: every ledger entry
# that is neither `terminal` nor `skipped` still has work owed, and goal-run
# already knows what to do with each shape -- a recorded session id is continued,
# an entry back at `queued` is opened first.  So the list is read from the
# ledger rather than retyped, and nothing that already reached a verdict is
# touched.
if [[ $CONTINUE -eq 1 ]]; then
    [[ -n "$WAVE" ]] && die "--continue does not apply to --wave"
    LEDGER="$WAVE_DIR/all.goalrun/ledger.json"
    [[ -f "$LEDGER" ]] || die "No ledger at $LEDGER -- there is no pool to continue"

    read -r -a PENDING <<< "$(python3 - "$LEDGER" <<'PY'
import json, sys
runs = json.load(open(sys.argv[1]))["runs"]
print(" ".join(r["concept"] for r in runs
                if r["phase"] not in ("terminal", "skipped")))
PY
    )"
    [[ ${#PENDING[@]} -gt 0 ]] || die "Nothing unfinished in $LEDGER"

    echo "== continuing ${#PENDING[@]} concept(s) from $LEDGER"
    echo "   ${PENDING[*]}"

    # No `replay --check` preflight here, unlike the replay pool below: the
    # concepts carrying a session are already open, and `replay` refuses a
    # concept that is not terminal.  `--mode replay` still reaches the entries
    # sitting at `queued` -- the ones a failed dependency stopped before they
    # were ever opened -- and skips the rest, since goal-run only opens a
    # concept whose phase is `queued`.
    exec uv run mimic_utils goal-run "${PENDING[@]}" \
        --name all --run-dir "$WAVE_DIR/all.goalrun" \
        -k "$PARALLEL" --mode replay --reason "$REPLAY_REASON" \
        "${DRY[@]+"${DRY[@]}"}" "${EXTRA[@]+"${EXTRA[@]}"}"
fi

# --------------------------------------------------------------------------- #
# the two that fail today's lint
# --------------------------------------------------------------------------- #

if [[ $RELINT -eq 1 ]]; then
    [[ -n "$WAVE" ]] && die "--wave does not apply to --relint"
    exec uv run mimic_utils goal-run "${RELINT_CONCEPTS[@]}" \
        -k "$PARALLEL" --mode reopen --reason "$RELINT_REASON" \
        "${DRY[@]+"${DRY[@]}"}" "${EXTRA[@]+"${EXTRA[@]}"}"
fi

# --------------------------------------------------------------------------- #
# the three that need re-authoring
# --------------------------------------------------------------------------- #

if [[ $REIMPLEMENT -eq 1 ]]; then
    [[ -n "$WAVE" ]] && die "--wave does not apply to --reimplement"

    # These must already be open: the reopen carries itemid-level instructions
    # that belong in the audit trail, and this script is not the place to
    # paraphrase them.  A concept still holding a verdict would be silently
    # skipped by --mode none, so refuse instead.
    unopened=()
    for c in "${REIMPLEMENT_CONCEPTS[@]}"; do
        status=$(python3 - "$c" <<'PY'
import json, pathlib, sys
p = pathlib.Path("mimic-iv/concepts_fhir/state") / sys.argv[1] / "state.json"
print(json.loads(p.read_text())["status"] if p.is_file() else "MISSING")
PY
        )
        printf '  %-20s %s\n' "$c" "$status"
        case "$status" in
            COMPLETED|COMPLETED_WITH_DIVERGENCE|BLOCKED_REPRESENTATION|MISSING)
                unopened+=("$c") ;;
        esac
    done
    if [[ ${#unopened[@]} -gt 0 ]]; then
        die "
Not reopened yet: ${unopened[*]}
Run the reopen + carryover-invalidate calls from section 5 of
TODO_upstream_fix_rerun.md first -- they carry the itemids and the explicit
\"this declaration is now FALSE\" instruction, and they are the audit record."
    fi

    exec uv run mimic_utils goal-run "${REIMPLEMENT_CONCEPTS[@]}" \
        -k "$PARALLEL" --mode none --reason "$REIMPLEMENT_REASON" \
        "${DRY[@]+"${DRY[@]}"}" "${EXTRA[@]+"${EXTRA[@]}"}"
fi

# --------------------------------------------------------------------------- #
# the replays
# --------------------------------------------------------------------------- #

if [[ -n "$WAVE" ]]; then
    LIST_FILE="$WAVE_DIR/wave${WAVE}.txt"
    [[ -f "$LIST_FILE" ]] || die "No wave list at $LIST_FILE"
    read -r -a LISTED <<< "$(tr '\n' ' ' < "$LIST_FILE")"
    RUN_NAME="$WAVE"
else
    # wave0 wave1 wave2 in glob order, which is already DAG order. goal-run
    # gates each concept on its own dependencies and has no barrier, so running
    # the combined list keeps the pool saturated instead of making wave 1 wait
    # for all of wave 0.
    read -r -a LISTED <<< "$(cat "$WAVE_DIR"/wave*.txt | tr '\n' ' ')"
    RUN_NAME="all"
fi
[[ ${#LISTED[@]} -gt 0 ]] || die "No concepts found under $WAVE_DIR"

# The relint concepts are in the wave lists but cannot be replayed, so drop them
# -- out loud, because a silent exclusion reads as full coverage. Their rerun is
# `--relint`, and it must land first: milrinone gates vasoactive_agent, and
# `replay` refuses a dependent whose dependency is not COMPLETED.
CONCEPTS=()
DROPPED=()
for c in "${LISTED[@]}"; do
    skip=0
    for r in "${RELINT_CONCEPTS[@]}"; do
        [[ "$c" == "$r" ]] && skip=1
    done
    if ((skip)); then DROPPED+=("$c"); else CONCEPTS+=("$c"); fi
done
if [[ ${#DROPPED[@]} -gt 0 ]]; then
    echo "== excluded from the replay pool: ${DROPPED[*]}"
    echo "   they fail today's resource-key lint, so a byte-identical replay is"
    echo "   refused at the demo gate. Run './rerun_fixed_build.sh --relint' first."
fi
[[ ${#CONCEPTS[@]} -gt 0 ]] || die "Nothing left to replay after exclusions"

# Concepts are always named explicitly rather than via --wave, since the wave
# file still lists the exclusions. --run-dir keeps the per-wave bookkeeping that
# --wave would otherwise have given us.
TARGET=("${CONCEPTS[@]}" --name "$RUN_NAME" --run-dir "$WAVE_DIR/${RUN_NAME}.goalrun")

# Preflight.  A refusal costs nothing here and cannot be undone once `replay`
# has spent the reopen, so every concept is checked before any is touched -- and
# all refusals are reported, not just the first.
echo "== preflight: replay --check over ${#CONCEPTS[@]} concept(s)"
refused=()
for c in "${CONCEPTS[@]}"; do
    if ! uv run mimic_utils replay "$c" --check; then
        refused+=("$c")
    fi
done
if [[ ${#refused[@]} -gt 0 ]]; then
    die "
Refused (${#refused[@]}): ${refused[*]}
Nothing was opened. A refusal means a fix made this port's mapping incomplete,
so replaying it byte-identical would re-earn its verdict against a declaration
that is no longer true. Read the refusal, then either re-implement the concept
or drop it from the list."
fi
echo "== preflight clean"

if [[ $CHECK_ONLY -eq 1 ]]; then
    exit 0
fi

exec uv run mimic_utils goal-run "${TARGET[@]}" \
    -k "$PARALLEL" --reason "$REPLAY_REASON" \
    "${DRY[@]+"${DRY[@]}"}" "${EXTRA[@]+"${EXTRA[@]}"}"
