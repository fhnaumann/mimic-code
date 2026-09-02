#!/usr/bin/env python3
"""Keep Library.*.json in sync with its sibling readability .sql file.

Each concept carries its SQL in three places that must agree:
  1. the readability <concept>.sql file (header comment + SQL body)
  2. Library.*.json -> content[0].extension[sql-text].valueString
  3. Library.*.json -> content[0].data  (base64 of the same body)

--check verifies all three agree for every concept; --write regenerates (2) and (3)
from the body of (1).
"""
import base64
import glob
import json
import os
import sys

SQL_TEXT_EXT = "http://hl7.org/fhir/uv/sql-on-fhir/StructureDefinition/sql-text"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "artifacts-curated")


def split_header(sql_file_text):
    """Return (header, body). The header is the leading comment block plus its
    trailing blank line; the body is what the Library stores."""
    lines = sql_file_text.split("\n")
    i = 0
    while i < len(lines) and lines[i].startswith("--"):
        i += 1
    while i < len(lines) and lines[i].strip() == "":
        i += 1
    return "\n".join(lines[:i]) + "\n" if i else "", "\n".join(lines[i:])


def library_body(lib):
    content = lib["content"][0]
    value = None
    for ext in content.get("extension", []) or []:
        if ext.get("url") == SQL_TEXT_EXT:
            value = ext.get("valueString")
    data = base64.b64decode(content["data"]).decode("utf-8")
    return value, data


def concepts():
    for lib_path in sorted(glob.glob(os.path.join(ROOT, "**", "Library.*.json"), recursive=True)):
        d = os.path.dirname(lib_path)
        sqls = glob.glob(os.path.join(d, "*.sql"))
        if len(sqls) == 1:
            yield lib_path, sqls[0]


def main():
    write = "--write" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    bad = changed = total = 0
    for lib_path, sql_path in concepts():
        if only and not any(o in lib_path for o in only):
            continue
        total += 1
        lib = json.load(open(lib_path))
        _, body = split_header(open(sql_path).read())
        value, data = library_body(lib)
        if write:
            if value == body and data == body:
                continue
            content = lib["content"][0]
            for ext in content.get("extension", []) or []:
                if ext.get("url") == SQL_TEXT_EXT:
                    ext["valueString"] = body
            content["data"] = base64.b64encode(body.encode("utf-8")).decode("ascii")
            with open(lib_path, "w") as fh:
                json.dump(lib, fh, indent=2)
                fh.write("\n")
            changed += 1
            print(f"synced  {os.path.relpath(lib_path, ROOT)}")
        else:
            problems = []
            if value != body:
                problems.append("sql-text != .sql body")
            if data != body:
                problems.append("base64 data != .sql body")
            if problems:
                bad += 1
                print(f"MISMATCH {os.path.relpath(lib_path, ROOT)}: {'; '.join(problems)}")
    if write:
        print(f"\n{changed} library file(s) synced out of {total} checked")
    else:
        print(f"\n{total} concept(s) checked, {bad} mismatch(es)")
    return 1 if (not write and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
