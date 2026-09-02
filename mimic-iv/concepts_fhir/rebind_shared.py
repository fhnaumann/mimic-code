#!/usr/bin/env python3
"""Repoint concept Libraries at the shared ViewDefinitions in _shared/.

Each concept keeps its own `relatedArtifact.label` -- that label is the table name
its SQL uses, and labels are Library-scoped -- but the `resource` it points at
becomes a shared canonical URL. The per-concept ViewDefinition file is then removed.

A rebind is only performed when the shared view's column names are a superset of the
per-concept view's, and when the two agree on row cardinality. Cardinality is
guaranteed structurally by grouping on (resource, grain, extraction form): a view
that filters rows via `forEach` is never merged with one that keeps them via an
inline path.

Usage:  rebind_shared.py [--write] [Resource ...]
"""
import glob
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts-curated")
SHARED = os.path.join(ROOT, "_shared")
ICU = "encounter-icu"
HOSP = "encounter-hosp"


def columns(view):
    """name -> (forEach-context, path) for every column in a ViewDefinition."""
    out = {}

    def walk(node, fe):
        if "forEach" in node:
            fe = fe + ("forEach:" + node["forEach"],)
        if "forEachOrNull" in node:
            fe = fe + ("orNull:" + node["forEachOrNull"],)
        for c in node.get("column", []) or []:
            out[c["name"]] = (fe, c["path"])
        for s in node.get("select", []) or []:
            walk(s, fe)
        for u in node.get("unionAll", []) or []:
            walk(u, fe)

    for s in view.get("select", []) or []:
        walk(s, ())
    return out


def classify(view):
    """Group key: resource plus the exact set of forEach contexts the view uses.

    Two views may only be merged when they iterate the same collections. A view
    with `forEach` on an identifier drops resources lacking it; one that reads the
    same identifier through an inline path keeps them with nulls; and two views
    with *different* forEach expressions would cross-join if combined. Keying on
    the exact signature makes all three cases distinct groups, so a merge can
    never change a consumer's row count.
    """
    sig = sorted({fe for fe, _ in columns(view).values()})
    return view["resource"] + "|" + "||".join("&&".join(fe) for fe in sig)


def shared_views():
    out = {}
    for path in sorted(glob.glob(os.path.join(SHARED, "ViewDefinition.*.json"))):
        v = json.load(open(path))
        out[classify(v)] = (v, path)
    return out


def main():
    write = "--write" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    shared = shared_views()
    if not shared:
        print(f"no shared views in {SHARED}")
        return 1

    rebound = removed = 0
    problems = []
    for lib_path in sorted(glob.glob(os.path.join(ROOT, "**", "Library.*.json"), recursive=True)):
        cdir = os.path.dirname(lib_path)
        lib = json.load(open(lib_path))
        changed = False
        for vd_path in sorted(glob.glob(os.path.join(cdir, "ViewDefinition*.json"))):
            v = json.load(open(vd_path))
            if only and v["resource"] not in only:
                continue
            key = classify(v)
            if key not in shared:
                continue
            sv, _ = shared[key]
            mine, theirs = columns(v), columns(sv)
            missing = {n: p for n, p in mine.items() if n not in theirs}
            differing = {
                n: (p, theirs[n]) for n, p in mine.items() if n in theirs and theirs[n] != p
            }
            rel = os.path.relpath(vd_path, ROOT)
            if missing or differing:
                problems.append(
                    f"{rel} -> {key}: missing={sorted(missing)} differing={sorted(differing)}"
                )
                continue
            hits = [
                ra for ra in lib.get("relatedArtifact", []) or []
                if ra.get("resource") == v["url"]
            ]
            if len(hits) != 1:
                problems.append(f"{rel}: {len(hits)} relatedArtifact entries point at it")
                continue
            if write:
                hits[0]["resource"] = sv["url"]
                os.remove(vd_path)
            changed = True
            rebound += 1
            removed += 1
            print(f"  {rel}\n      label '{hits[0]['label']}' -> {sv['url']}")
        if changed and write:
            with open(lib_path, "w") as fh:
                json.dump(lib, fh, indent=2)
                fh.write("\n")

    if problems:
        print("\nNOT REBOUND:")
        for p in problems:
            print("  " + p)
    verb = "rebound" if write else "would rebind"
    print(f"\n{verb} {rebound} binding(s), {removed} per-concept ViewDefinition(s) removed"
          f"{'' if write else ' (dry run -- pass --write)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
