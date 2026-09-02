#!/usr/bin/env python3
"""Verify every SQL column reference against the ViewDefinition it reads from.

For each concept, Library.relatedArtifact maps a label (the table name used in the
SQL) to a ViewDefinition URL. This resolves each label to that view's declared
column set, parses the SQL, and checks that every alias-qualified column reference
whose source is one of those base views actually exists on the view.

Catches renames applied to a ViewDefinition but missed in the SQL (and vice versa).
Labels pointing at other concept Libraries are skipped -- their columns come from a
downstream SELECT, not a ViewDefinition.
"""
import glob
import json
import os
import sys

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import build_scope

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts-curated")
DIALECT = "spark"


def view_columns(path):
    d = json.load(open(path))
    out = set()

    def walk(node):
        for c in node.get("column", []) or []:
            out.add(c["name"])
        for s in node.get("select", []) or []:
            walk(s)
        for u in node.get("unionAll", []) or []:
            walk(u)

    for s in d.get("select", []) or []:
        walk(s)
    return d["url"], out


def main():
    problems = 0
    checked_refs = 0
    concepts = 0

    for lib_path in sorted(glob.glob(os.path.join(ROOT, "**", "Library.*.json"), recursive=True)):
        cdir = os.path.dirname(lib_path)
        sqls = glob.glob(os.path.join(cdir, "*.sql"))
        if len(sqls) != 1:
            continue
        lib = json.load(open(lib_path))

        by_url = {}
        for vd in glob.glob(os.path.join(cdir, "ViewDefinition*.json")):
            url, cols = view_columns(vd)
            by_url[url] = (cols, os.path.basename(vd))

        # label -> (columns, viewdef filename); only ViewDefinition-backed labels
        schema = {}
        for ra in lib.get("relatedArtifact", []) or []:
            res = ra.get("resource", "")
            if res in by_url:
                schema[ra["label"]] = by_url[res]
        if not schema:
            continue
        concepts += 1

        sql = open(sqls[0]).read()
        try:
            tree = sqlglot.parse_one(sql, read=DIALECT)
        except Exception as e:
            print(f"PARSE FAIL {os.path.relpath(sqls[0], ROOT)}: {e}")
            problems += 1
            continue

        root = build_scope(tree)
        if root is None:
            continue
        for scope in root.traverse():
            # alias -> base view label for this scope only
            local = {}
            for alias, source in scope.selected_sources.items():
                node = source[1] if isinstance(source, tuple) else source
                if isinstance(node, exp.Table):
                    name = node.name
                    if name in schema:
                        local[alias] = name
            if not local:
                continue
            for col in scope.expression.find_all(exp.Column):
                tbl = col.table
                if not tbl or tbl not in local:
                    continue
                label = local[tbl]
                cols, vd_name = schema[label]
                checked_refs += 1
                if col.name not in cols:
                    problems += 1
                    print(
                        f"UNRESOLVED {os.path.relpath(sqls[0], ROOT)}: "
                        f"{tbl}.{col.name} -- view '{label}' ({vd_name}) declares "
                        f"{sorted(cols)}"
                    )

    print(
        f"\n{concepts} concept(s) with ViewDefinition-backed tables, "
        f"{checked_refs} column reference(s) checked, {problems} problem(s)"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
