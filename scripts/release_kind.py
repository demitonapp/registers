#!/usr/bin/env python3
"""What kind of release a tag is, computed from the diff against the previous tag.

    python3 scripts/release_kind.py --base v15                       # what HEAD carries
    python3 scripts/release_kind.py --base v15 --tag v16 --out dist/RELEASE.json

A change to the obligation library reaches a customer on one of three release clocks:

  addition    a new instrument, a jurisdiction switched to `supported`, or a new
              duty the library did not carry. Ships with the release it is tagged
              in; releases are cut and deployed when needed, with no fixed cadence.
  amendment   a version in force from a date after the tag, or a repeal (an
              `until`) on or after it. Ships ahead of commencement.
  correction  Demiton's row was wrong: a changed field of an existing version, a
              removed key, or a new version in force on or before the tag date.
              Ships the same day.

Like `bump_check.py`, this computes what a change requires instead of trusting a
label. Each tree is flattened by its own tag's `resolve.flatten()`, and every row is
compared by `(key, version)`, where a version is named by its `in_force.from` date,
or `original` when it has none. A newly dated version with a `from` after the tag date
is an `amendment` (and the version before it gains a derived `until`, a repeal after the
tag); a `from` on or before the tag date is a `correction`.

One case is ambiguous: a new key with no `from` in an instrument that already
existed. It is a duty the library missed (a correction) or one it now adds (an
addition), and only its author knows which. It computes as `addition`, and the
CHANGELOG section may declare `correction` instead: either kind satisfies the
check, so the declaration is the resolution.

With `--tag`, CHANGELOG.md at the head must carry `## vN, YYYY-MM-DD: <kinds>` naming
every computed kind; the tag is refused otherwise, and `--out` writes RELEASE.json
(`{tag, kinds, amendments: [{key, from}]}`) for the monorepo's release gate.

Exit code 1 when the tag is refused. An amendment commencing fewer than 20 business
days after the tag date is a warning only.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("addition", "amendment", "correction")
AMENDMENT_LEAD_BUSINESS_DAYS = 20
HEADING = re.compile(r"^## (v\d+), (\d{4}-\d{2}-\d{2}): (.*)$", re.M)


@dataclass(frozen=True)
class Tree:
    instruments: list[dict]
    supported: frozenset[str]


@dataclass(frozen=True)
class Change:
    kind: str
    key: str
    reason: str
    alt: str | None = None  # a kind the CHANGELOG may declare instead
    commences: date | None = None  # an amendment's commencement


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def tree_at(ref: str) -> Tree:
    """The flattened library and the supported jurisdictions at `ref`, flattened by
    that ref's own resolver, so an old tag reads the way it shipped."""
    with tempfile.TemporaryDirectory() as tmp:
        tarfile.open(fileobj=io.BytesIO(_git("archive", ref, "obligations", "vocab", "scripts"))).extractall(tmp, filter="data")
        spec = importlib.util.spec_from_file_location(f"resolve_at_{abs(hash(ref))}", Path(tmp) / "scripts" / "resolve.py")
        resolve = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolve)
        instruments = resolve.flatten()
        vocab = json.loads((Path(tmp) / "vocab" / "jurisdictions.json").read_text())
    return Tree(instruments, frozenset(c for c, v in vocab.items() if isinstance(v, dict) and v.get("supported")))


def _date(value: object) -> date | None:
    if value is None:
        return None
    return value if isinstance(value, date) else date.fromisoformat(str(value))


def _in_force(row: dict, field: str) -> date | None:
    return _date((row.get("in_force") or {}).get(field))


def _rows(tree: Tree) -> dict[tuple[str, str], tuple[str, dict]]:
    """`(key, version) -> (instrument id, row)`. The instrument's header, less any
    `in_force` (the resolver copies that onto rows), is folded into each row: a
    changed citation or title changes every row that reads it."""
    out = {}
    for inst in tree.instruments:
        header = {k: v for k, v in inst.items() if k not in ("obligations", "in_force")}
        for row in inst["obligations"]:
            version = str(_in_force(row, "from") or "original")
            out[(row["key"], version)] = (inst["id"], {**row, "_instrument": header})
    return out


def _without_until(row: dict) -> dict:
    """The row less what the resolver derives from its neighbours: the `until` (and
    `until_by`) of an earlier version, and the `by` of a version with no `from`, which is
    its until's. Dating a new version derives these onto the version before it, and that
    is not a changed field of the earlier one."""
    block = {k: v for k, v in (row.get("in_force") or {}).items() if k not in ("until", "until_by")}
    if "from" not in block:
        block.pop("by", None)
    return {**row, "in_force": block}


def classify(old: Tree, new: Tree, on: date) -> list[Change]:
    """Every difference between two flattened trees, each with its kind. `on` is the
    tag date."""
    changes = [Change("addition", code, "jurisdiction switched to supported") for code in sorted(new.supported - old.supported)]
    before, after = _rows(old), _rows(new)
    old_ids = {inst["id"] for inst in old.instruments}
    old_keys = {key for key, _ in before}
    for (key, version), (iid, row) in after.items():
        start = _in_force(row, "from")
        if (key, version) in before:
            prior = before[(key, version)][1]
            until = _in_force(row, "until")
            if until != _in_force(prior, "until"):
                if until and until >= on:
                    changes.append(Change("amendment", key, "repealed after the tag date", commences=until + timedelta(days=1)))
                else:
                    changes.append(Change("correction", key, "in-force-until changed on or before the tag date"))
            if _without_until(row) != _without_until(prior):
                changes.append(Change("correction", key, "changed field of an existing version"))
        elif iid not in old_ids:
            changes.append(Change("addition", key, f"new instrument {iid}"))
        elif start and start > on:
            changes.append(Change("amendment", key, "in force from after the tag date", commences=start))
        elif start or key in old_keys:
            changes.append(Change("correction", key, "new version in force on or before the tag date"))
        else:
            changes.append(Change("addition", key, f"new key in existing instrument {iid}", alt="correction"))
    changes += [Change("correction", key, "removed") for key, version in before if (key, version) not in after]
    return changes


def computed_kinds(changes: list[Change]) -> set[str]:
    return {c.kind for c in changes}


def business_days_between(start: date, end: date) -> int:
    """Weekdays after `start` up to and including `end`."""
    # ponytail: Monday to Friday only, no public holidays; a jurisdiction's calendar if the lead ever turns on one day
    return sum(1 for n in range(1, (end - start).days + 1) if (start + timedelta(days=n)).weekday() < 5)


def declared(changelog: str, tag: str) -> set[str] | None:
    """The kinds a `## vN, YYYY-MM-DD: <kinds>` section declares, or None when
    the CHANGELOG has no section for `tag`."""
    for found in HEADING.finditer(changelog):
        if found.group(1) == tag:
            return set(re.findall(r"\b(" + "|".join(KINDS) + r")\b", found.group(3)))
    return None


def refusals(changes: list[Change], changelog: str, tag: str, on: date) -> list[str]:
    kinds = declared(changelog, tag)
    if kinds is None:
        return [f"CHANGELOG.md has no `## {tag}, YYYY-MM-DD: <kinds>` section"]
    errors = []
    for kind, n in Counter(c.kind for c in changes if c.kind not in kinds and c.alt not in kinds).items():
        example = next(c for c in changes if c.kind == kind and c.kind not in kinds and c.alt not in kinds)
        errors.append(f"{n} change(s) are `{kind}` but the {tag} section does not declare it (e.g. {example.key}: {example.reason})")
    return errors


def release_json(changes: list[Change], changelog: str, tag: str) -> dict:
    kinds = declared(changelog, tag)
    amendments = sorted({(c.key, c.commences) for c in changes if c.kind == "amendment"})
    return {
        "tag": tag,
        "kinds": [k for k in KINDS if k in kinds],
        "amendments": [{"key": key, "from": start.isoformat()} for key, start in amendments],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="the previous release tag, e.g. v15")
    ap.add_argument("--head", default="HEAD", help="the ref being released (default HEAD)")
    ap.add_argument("--tag", help="the tag being cut: check its CHANGELOG section")
    ap.add_argument("--on", type=date.fromisoformat, default=date.today(), help="the tag date (default today)")
    ap.add_argument("--out", help="with --tag, write RELEASE.json here")
    args = ap.parse_args()

    changes = classify(tree_at(args.base), tree_at(args.head), args.on)
    for (kind, reason), n in sorted(Counter((c.kind, c.reason) for c in changes).items()):
        print(f"{kind:<11} {n:>4}  {reason}")
    print(f"kinds: {', '.join(k for k in KINDS if k in computed_kinds(changes)) or 'none'}")
    for c in changes:
        if c.kind == "amendment" and business_days_between(args.on, c.commences) < AMENDMENT_LEAD_BUSINESS_DAYS:
            print(f"warning: {c.key} commences {c.commences}, fewer than {AMENDMENT_LEAD_BUSINESS_DAYS} business days after {args.on}")

    if not args.tag:
        return 0
    changelog = _git("show", f"{args.head}:CHANGELOG.md").decode()
    errors = refusals(changes, changelog, args.tag, args.on)
    for e in errors:
        print(f"error: {e}")
    if errors:
        return 1
    if args.out:
        Path(args.out).write_text(json.dumps(release_json(changes, changelog, args.tag), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
