#!/usr/bin/env python3
"""Refuse a contract that would name a tenant or an internal implementation
detail (spec 09 Section 4, decision 3's allowlist made a second, independent
check).

    python3 scripts/leak_check.py

Two layers:
  1. The same pattern the Demiton API's own publish allowlist refuses to serve
     (`\\bPCA\\b|census`, word-bounded so a code token like `pca_ref` still passes -
     renaming that token is a contract change, catchable by a human reviewer, not
     a false positive here).
  2. A tenant name denylist, read from the `REGISTERS_TENANT_DENYLIST` environment
     variable (comma-separated), never committed to this repository. CI sets it
     from a GitHub Actions secret; a local run without it checks layer 1 only and
     says so, rather than silently passing as if layer 2 had run clean.

Exit code 1 if any contract or history document matches either layer.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEAK = re.compile(r"\bPCA\b|census", re.IGNORECASE)


def _denylist_pattern() -> re.Pattern[str] | None:
    raw = os.environ.get("REGISTERS_TENANT_DENYLIST", "").strip()
    if not raw:
        return None
    names = [re.escape(n.strip()) for n in raw.split(",") if n.strip()]
    return re.compile(r"\b(" + "|".join(names) + r")\b", re.IGNORECASE) if names else None


def check() -> list[str]:
    errors: list[str] = []
    denylist = _denylist_pattern()
    for path in sorted(ROOT.glob("contracts/*.schema.json")) + sorted(ROOT.glob("history/*/*.schema.json")):
        text = path.read_text()
        rel = path.relative_to(ROOT)
        hit = LEAK.search(text)
        if hit:
            errors.append(f"{rel}: matches the tenant/internal pattern near ...{text[max(0, hit.start()-40):hit.end()+40]}...")
            continue
        if denylist:
            hit2 = denylist.search(text)
            if hit2:
                errors.append(f"{rel}: matches the tenant denylist near ...{text[max(0, hit2.start()-40):hit2.end()+40]}...")
    return errors


def main() -> int:
    errors = check()
    for e in errors:
        print(f"error: {e}")
    if not os.environ.get("REGISTERS_TENANT_DENYLIST"):
        print("warning: REGISTERS_TENANT_DENYLIST is not set - only the fixed pattern was checked", file=sys.stderr)
    checked = len(list(ROOT.glob("contracts/*.schema.json"))) + len(list(ROOT.glob("history/*/*.schema.json")))
    print(f"{len(errors)} error(s), {checked} document(s) checked")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
