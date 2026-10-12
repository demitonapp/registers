#!/usr/bin/env python3
"""What kind of release a tag is, computed from the diff against the previous tag.

    python3 scripts/release_kind.py --base v15                       # what HEAD carries
    python3 scripts/release_kind.py --base v15 --tag v16 --out dist/RELEASE.json

A change to the obligation library reaches a customer on one of three release clocks:

  wave        an addition: a new instrument, or a jurisdiction switched to
              `supported`. Production takes it only on its wave date, the first
              Monday of February, May, August or November.
  amendment   a version in force from a date after the tag, or a repeal (an
              `until`) on or after it. Ships ahead of commencement.
  correction  Demiton's row was wrong: a changed field of an existing version, a
              removed key, or a new version in force on or before the tag date.
              Ships the same day.

Like `bump_check.py`, this computes what a change requires instead of trusting a
label. Each tree is flattened by its own tag's `resolve.flatten()`, and every row is
compared by `(key, version)`, where a version is named by its `in_force.from` date,
or `original` when it has none (none has one until dated versions land).

One case is ambiguous: a new key with no `from` in an instrument that already
existed. It is a duty the library missed (a correction) or one it now adds (a wave),
and only its author knows which. It computes as `wave`, and the CHANGELOG section may
declare `correction` instead: either kind satisfies the check, so the declaration is
the resolution.

With `--tag`, CHANGELOG.md at the head must carry `## vN, YYYY-MM-DD: <kinds>` naming
every computed kind, with `wave of YYYY-MM-DD` when a wave is among them; the tag is
refused otherwise, and `--out` writes RELEASE.json
(`{tag, kinds, wave_on, amendments: [{key, from}]}`) for the monorepo's release gate.

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
KINDS = ("wave", "amendment", "correction")
WAVE_MONTHS = (2, 5, 8, 11)
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
    return {**row, "in_force": {k: v for k, v in (row.get("in_force") or {}).items() if k != "until"}}


def classify(old: Tree, new: Tree, on: date) -> list[Change]:
    """Every difference between two flattened trees, each with its kind. `on` is the
    tag date."""
    changes = [Change("wave", code, "jurisdiction switched to supported") for code in sorted(new.supported - old.supported)]
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
            changes.append(Change("wave", key, f"new instrument {iid}"))
        elif start and start > on:
            changes.append(Change("amendment", key, "in force from after the tag date", commences=start))
        elif start or key in old_keys:
            changes.append(Change("correction", key, "new version in force on or before the tag date"))
        else:
            changes.append(Change("wave", key, f"new key in existing instrument {iid}", alt="correction"))
    changes += [Change("correction", key, "removed") for key, version in before if (key, version) not in after]
    return changes


def computed_kinds(changes: list[Change]) -> set[str]:
    return {c.kind for c in changes}


def business_days_between(start: date, end: date) -> int:
    """Weekdays after `start` up to and including `end`."""
    # ponytail: Monday to Friday only, no public holidays; a jurisdiction's calendar if the lead ever turns on one day
    return sum(1 for n in range(1, (end - start).days + 1) if (start + timedelta(days=n)).weekday() < 5)


def is_wave_day(day: date) -> bool:
    return day.month in WAVE_MONTHS and day.weekday() == 0 and day.day <= 7


def declared(changelog: str, tag: str) -> tuple[set[str], date | None] | None:
    """The kinds and wave date a `## vN, YYYY-MM-DD: <kinds>` section declares, or
    None when the CHANGELOG has no section for `tag`."""
    for found in HEADING.finditer(changelog):
        if found.group(1) == tag:
            rest = found.group(3)
            wave_of = re.search(r"wave of (\d{4}-\d{2}-\d{2})", rest)
            return set(re.findall(r"\b(" + "|".join(KINDS) + r")\b", rest)), _date(wave_of and wave_of.group(1))
    return None


def refusals(changes: list[Change], changelog: str, tag: str, on: date) -> list[str]:
    section = declared(changelog, tag)
    if section is None:
        return [f"CHANGELOG.md has no `## {tag}, YYYY-MM-DD: <kinds>` section"]
    kinds, wave_on = section
    errors = []
    for kind, n in Counter(c.kind for c in changes if c.kind not in kinds and c.alt not in kinds).items():
        example = next(c for c in changes if c.kind == kind and c.kind not in kinds and c.alt not in kinds)
        errors.append(f"{n} change(s) are `{kind}` but the {tag} section does not declare it (e.g. {example.key}: {example.reason})")
    if "wave" in kinds:
        if wave_on is None:
            errors.append(f"the {tag} section declares a wave but no `wave of YYYY-MM-DD`")
        elif not is_wave_day(wave_on):
            errors.append(f"wave of {wave_on} is not the first Monday of February, May, August or November")
        elif wave_on < on:
            errors.append(f"wave of {wave_on} is before the tag date {on}")
    return errors


def release_json(changes: list[Change], changelog: str, tag: str) -> dict:
    kinds, wave_on = declared(changelog, tag)
    amendments = sorted({(c.key, c.commences) for c in changes if c.kind == "amendment"})
    return {
        "tag": tag,
        "kinds": [k for k in KINDS if k in kinds],
        "wave_on": wave_on.isoformat() if wave_on and "wave" in kinds else None,
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
