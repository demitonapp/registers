#!/usr/bin/env python3
"""One semver rule for every register, tenant, platform or research (spec 09
Section 4 P2, replacing the two separate rules the monorepo and disease-economics
used to run).

    python3 scripts/bump_check.py --base origin/main

MAJOR - a property removed, a new requirement, an enum narrowed, a type changed:
         existing documents may stop validating.
MINOR - a property added, an enum widened: every existing document still validates.
PATCH - anything else (a description, a pattern's wording, an example).

Ported from disease-economics' `schema_bump_needed` (itself the rule the monorepo's
shelf contracts already used, SD024 decision 15), including the 2026-09-26 fix: a
`required` list inside a property that did not exist before is not a new
requirement on existing documents - the whole property is new, and only optional
unless the *parent* now requires it too.

Exit code 1 if any changed contract's version key was not bumped enough.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_KEYS = ("x-schema-version", "x-demiton-contract-version")
# `allOf` branches and an `if`'s `then`/`else` validate the same document as the
# schema they sit in. A `required` there binds that document, not a new property.
# `if` itself is left alone: failing it invalidates nothing.
SAME_DOCUMENT = re.compile(r"(?:/allOf/\d+|/then|/else)+$")


def _version_key(doc: dict) -> str | None:
    return next((k for k in VERSION_KEYS if k in doc), None)


def _schema_facts(schema: object) -> dict:
    """The parts of a JSON Schema a version bump is judged on, keyed by JSON pointer."""
    facts: dict[str, dict] = {"props": {}, "required": {}, "enum": {}, "type": {}}

    def walk(node: object, ptr: str) -> None:
        if isinstance(node, dict):
            if isinstance(node.get("properties"), dict):
                facts["props"][ptr] = set(node["properties"])
            if isinstance(node.get("required"), list):
                facts["required"][ptr] = set(node["required"])
            if "enum" in node:
                facts["enum"][ptr] = {json.dumps(v) for v in node["enum"]}
            if "type" in node:
                facts["type"][ptr] = json.dumps(node["type"], sort_keys=True)
            for k, v in node.items():
                if k not in VERSION_KEYS:
                    walk(v, f"{ptr}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{ptr}/{i}")

    walk(schema, "#")
    return facts


def schema_bump_needed(old: dict, new: dict) -> str | None:
    """None if unchanged; else 'major', 'minor' or 'patch'."""
    strip = lambda s: {k: v for k, v in s.items() if k not in VERSION_KEYS}  # noqa: E731
    if strip(old) == strip(new):
        return None
    a, b = _schema_facts(old), _schema_facts(new)
    if (
        any(p not in b["props"] or not a["props"][p] <= b["props"][p] for p in a["props"])
        # A required list inside a property that did not exist before cannot break an
        # existing document (the whole property is new, unless the parent requires it).
        # A required list under allOf/then/else binds its parent's document: judge it there.
        or any(
            not b["required"][p] <= a["required"].get(p, set())
            for p in b["required"]
            if (doc := SAME_DOCUMENT.sub("", p)) in a["props"] or doc in a["required"]
        )
        or any(p in b["enum"] and not a["enum"][p] <= b["enum"][p] for p in a["enum"])
        or any(p in b["type"] and a["type"][p] != b["type"][p] for p in a["type"])
    ):
        return "major"
    if any(b["props"][p] - a["props"].get(p, set()) for p in b["props"]) or any(
        b["enum"][p] - a["enum"].get(p, set()) for p in b["enum"]
    ):
        return "minor"
    return "patch"


def _bumped_enough(old_v: str, new_v: str, level: str) -> bool:
    o, n = tuple(map(int, SEMVER.match(old_v).groups())), tuple(map(int, SEMVER.match(new_v).groups()))
    if level == "major":
        return n[0] > o[0]
    if level == "minor":
        return n[0] > o[0] or (n[0] == o[0] and n[1] > o[1])
    return n > o


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout


def check_against_base(base: str) -> list[str]:
    errors = []
    changed_contracts = {
        p for p in _git("diff", "--name-only", base, "--", "contracts/", "research/").splitlines()
        if p.endswith(".schema.json")
    }
    for rel in sorted(changed_contracts):
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: a register contract is never deleted - deprecate it instead")
            continue
        try:
            old_text = _git("show", f"{base}:{rel}")
        except subprocess.CalledProcessError:
            continue  # new file, nothing to compare against
        old, new = json.loads(old_text), json.loads(path.read_text())
        level = schema_bump_needed(old, new)
        if level is None:
            continue
        old_key, new_key = _version_key(old), _version_key(new)
        if not old_key or not new_key:
            errors.append(f"{rel}: this is a {level.upper()} change but has no version key to check against")
            continue
        ov, nv = str(old.get(old_key, "")), str(new.get(new_key, ""))
        if SEMVER.match(ov) and SEMVER.match(nv) and not _bumped_enough(ov, nv, level):
            errors.append(f"{rel}: this is a {level.upper()} change - bump {new_key} from {ov} accordingly (now {nv})")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True, help="git ref to compare against, e.g. origin/main")
    args = ap.parse_args()
    errors = check_against_base(args.base)
    for e in errors:
        print(f"error: {e}")
    print(f"{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
