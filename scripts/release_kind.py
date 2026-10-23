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

Two inputs beside the obligation library change what a customer gets, and are read the
same way (each tree at its own tag):

  holidays/   a content diff of any file under `holidays/` (parsed, so a reflowed file is
              no change). A calendar that only gains holidays in years it did not list,
              with its other fields unchanged (`sources` may grow), is an `addition`;
              any other content change (a changed or removed date, a new date in a year
              the file already listed completely, a changed field, a removed file) is a
              `correction`, as a counted business day moves. A new file is an `addition`.
              The change is keyed by the file, and its reason names the file.
  vocab/      a jurisdiction in `vocab/jurisdictions.json` that was `supported` and no
              longer is (or is gone) is a `correction`; one switched on is an `addition`.
              No other vocabulary file is classified: a vocabulary entry reaches a
              customer through the rows that name it.

One case is ambiguous: a new key with no `from` in an instrument that already
existed. It is a duty the library missed (a correction) or one it now adds (an
addition), and only its author knows which. It computes as `addition`, and the
CHANGELOG section may declare `correction` instead: either kind satisfies the
check, so the declaration is the resolution.

With `--tag`, CHANGELOG.md at the head must carry `## vN, YYYY-MM-DD: <kinds>` naming
every computed kind (and have exactly one `## vN` heading, with a real calendar date); the
tag is refused otherwise, and `--out` writes RELEASE.json
(`{tag, kinds, amendments: [{key, from}], warnings: [str]}`) for the monorepo's release
gate.

The tag date is the date in that heading, not the runner's clock. It is the `--on` the
classification runs against, and the tag is refused when it differs from the date of the
tag commit in Australia/Brisbane (`--commit-date`, an ISO 8601 datetime such as
`git log -1 --format=%cI <tag>` prints; default: the head commit's). A runner's UTC
clock is a day behind Brisbane for ten hours of every day, so a clock is never the date.
Without `--tag` (a pull request's informational run), `--on` defaults to today in
Brisbane.

Exit code 1 when the tag is refused. An amendment commencing fewer than 20 business
days after the tag date (SM052 decision 16) is a warning only. It is reported once per
amendment, as a GitHub `::warning::` annotation under Actions (a `warning:` line
elsewhere), and the same text goes into RELEASE.json's `warnings` (`[]` when there are
none) and, in the release workflow, into the GitHub release notes under "Late
amendments". The monorepo's release gate reads `tag`, `kinds`, `amendments` and
`warnings`; the file has no other fields.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import yaml
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("addition", "amendment", "correction")
AMENDMENT_LEAD_BUSINESS_DAYS = 20
HEADING = re.compile(r"^## (v\d+), (\d{4}-\d{2}-\d{2}): (.*)$", re.M)
try:
    BRISBANE = ZoneInfo("Australia/Brisbane")
except ZoneInfoNotFoundError:  # a host with no tz database; Brisbane has had no daylight saving since 1992
    BRISBANE = timezone(timedelta(hours=10), "Australia/Brisbane")


@dataclass(frozen=True)
class Tree:
    instruments: list[dict]
    supported: frozenset[str]
    holidays: dict[str, object] = field(default_factory=dict)  # `holidays/<file>` -> its parsed content


@dataclass(frozen=True)
class Change:
    kind: str
    key: str
    reason: str
    alt: str | None = None  # a kind the CHANGELOG may declare instead
    commences: date | None = None  # an amendment's commencement


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def _holiday_files(directory: Path) -> dict[str, object]:
    """`holidays/<file>` -> parsed content, for every yaml and json file in `directory`."""
    out: dict[str, object] = {}
    for path in sorted(directory.glob("*")):
        if path.suffix in (".yaml", ".yml"):
            out[f"holidays/{path.name}"] = yaml.safe_load(path.read_text())
        elif path.suffix == ".json":
            out[f"holidays/{path.name}"] = json.loads(path.read_text())
    return out


def tree_at(ref: str) -> Tree:
    """The flattened library, the supported jurisdictions and the holiday calendars at
    `ref`, flattened by that ref's own resolver, so an old tag reads the way it shipped.
    A ref from before `holidays/` existed has none."""
    present = set(_git("ls-tree", "--name-only", ref).decode().split())
    paths = [p for p in ("obligations", "vocab", "scripts", "holidays") if p in present]
    with tempfile.TemporaryDirectory() as tmp:
        tarfile.open(fileobj=io.BytesIO(_git("archive", ref, *paths))).extractall(tmp, filter="data")
        spec = importlib.util.spec_from_file_location(f"resolve_at_{abs(hash(ref))}", Path(tmp) / "scripts" / "resolve.py")
        resolve = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(resolve)
        instruments = resolve.flatten()
        vocab = json.loads((Path(tmp) / "vocab" / "jurisdictions.json").read_text())
        holidays = _holiday_files(Path(tmp) / "holidays")
    return Tree(instruments, frozenset(c for c, v in vocab.items() if isinstance(v, dict) and v.get("supported")), holidays)


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


def _entry(item: object) -> str:
    return json.dumps(item, sort_keys=True, default=str)


def holiday_change(path: str, old: object, new: object) -> Change | None:
    """How one holiday file differs between two trees, or None when its content is the
    same. An addition only when the new calendar keeps every old entry, every old year and
    every other field, and each holiday it gains falls in a year the old file did not list
    (a date missing from a year the file listed as complete was a wrong calendar)."""
    if old == new:
        return None
    if old is None:
        return Change("addition", path, f"{path}: new holiday calendar")
    if new is None:
        return Change("correction", path, f"{path}: holiday calendar removed")
    if isinstance(old, dict) and isinstance(new, dict):
        grown = {"years", "holidays", "sources"}
        if all(old.get(k) == new.get(k) for k in (old.keys() | new.keys()) - grown):
            old_years, new_years = set(old.get("years") or []), set(new.get("years") or [])
            old_days = [_entry(h) for h in old.get("holidays") or []]
            new_days = {_entry(h): h for h in new.get("holidays") or []}
            old_sources = [_entry(x) for x in old.get("sources") or []]
            new_sources = {_entry(x) for x in new.get("sources") or []}
            gained = [h for e, h in new_days.items() if e not in old_days]
            if (
                old_years <= new_years
                and set(old_days) <= new_days.keys()
                and set(old_sources) <= new_sources
                and all(str(h.get("date", ""))[:4].isdigit() and int(str(h["date"])[:4]) not in old_years for h in gained)
            ):
                return Change("addition", path, f"{path}: holidays added for new years")
    return Change("correction", path, f"{path}: holiday dates or fields changed")


def classify(old: Tree, new: Tree, on: date) -> list[Change]:
    """Every difference between two flattened trees, each with its kind. `on` is the
    tag date."""
    changes = [Change("addition", code, "jurisdiction switched to supported") for code in sorted(new.supported - old.supported)]
    changes += [Change("correction", code, f"{code}: jurisdiction switched from supported to unsupported") for code in sorted(old.supported - new.supported)]
    for path in sorted(old.holidays.keys() | new.holidays.keys()):
        found = holiday_change(path, old.holidays.get(path), new.holidays.get(path))
        if found:
            changes.append(found)
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


def _sections(changelog: str, tag: str) -> list[re.Match]:
    return [found for found in HEADING.finditer(changelog) if found.group(1) == tag]


def heading_errors(changelog: str, tag: str) -> list[str]:
    """What is wrong with `tag`'s `## vN, YYYY-MM-DD: <kinds>` heading: absent, repeated (which
    of two would be the release?), or dated with a day that is not on the calendar."""
    found = _sections(changelog, tag)
    if not found:
        return [f"CHANGELOG.md has no `## {tag}, YYYY-MM-DD: <kinds>` section"]
    if len(found) > 1:
        return [f"CHANGELOG.md has {len(found)} `## {tag}` headings ({', '.join(m.group(2) for m in found)}); a tag has one section"]
    try:
        date.fromisoformat(found[0].group(2))
    except ValueError:
        return [f"the {tag} heading is dated {found[0].group(2)}, which is not a calendar date; use the tag date as YYYY-MM-DD"]
    return []


def declared(changelog: str, tag: str) -> set[str] | None:
    """The kinds a `## vN, YYYY-MM-DD: <kinds>` section declares, or None when
    the CHANGELOG has no section for `tag`."""
    found = _sections(changelog, tag)
    return set(re.findall(r"\b(" + "|".join(KINDS) + r")\b", found[0].group(3))) if found else None


def heading_date(changelog: str, tag: str) -> date | None:
    """The date in the `## vN, YYYY-MM-DD: <kinds>` heading of `tag`: the tag date. None when
    there is no heading; `ValueError` naming the text when its day is not on the calendar."""
    found = _sections(changelog, tag)
    return date.fromisoformat(found[0].group(2)) if found else None


def brisbane_date(moment: str | datetime) -> date:
    """The calendar date in Australia/Brisbane of an ISO 8601 datetime with an offset (or `Z`)."""
    when = datetime.fromisoformat(moment) if isinstance(moment, str) else moment
    if when.tzinfo is None:
        raise ValueError(f"{moment!r} has no UTC offset; pass an ISO 8601 datetime such as `git log --format=%cI` prints")
    return when.astimezone(BRISBANE).date()


def today_in_brisbane() -> date:
    return datetime.now(BRISBANE).date()


def late_amendments(changes: list[Change], on: date) -> list[str]:
    """One warning per amendment commencing fewer than 20 business days after `on`. A new
    version and the derived `until` of the version before it are one amendment, found twice
    (same key, same commencement), so they are counted once."""
    return [
        f"{key} commences {start}, fewer than {AMENDMENT_LEAD_BUSINESS_DAYS} business days after {on}"
        for key, start in sorted({(c.key, c.commences) for c in changes if c.kind == "amendment"})
        if business_days_between(on, start) < AMENDMENT_LEAD_BUSINESS_DAYS
    ]


def refusals(changes: list[Change], changelog: str, tag: str, on: date, commit_date: date | None = None) -> list[str]:
    errors = heading_errors(changelog, tag)
    if errors:
        return errors
    kinds = declared(changelog, tag)
    if commit_date is not None and heading_date(changelog, tag) != commit_date:
        errors.append(
            f"the {tag} section is dated {heading_date(changelog, tag)} but the tag commit is dated {commit_date} "
            f"in Australia/Brisbane; the heading date is the tag date, so set it to {commit_date}"
        )
    for kind, n in Counter(c.kind for c in changes if c.kind not in kinds and c.alt not in kinds).items():
        example = next(c for c in changes if c.kind == kind and c.kind not in kinds and c.alt not in kinds)
        errors.append(f"{n} change(s) are `{kind}` but the {tag} section does not declare it (e.g. {example.key}: {example.reason})")
    return errors


def release_json(changes: list[Change], changelog: str, tag: str, warnings: list[str] | None = None) -> dict:
    kinds = declared(changelog, tag)
    amendments = sorted({(c.key, c.commences) for c in changes if c.kind == "amendment"})
    return {
        "tag": tag,
        "kinds": [k for k in KINDS if k in kinds],
        "amendments": [{"key": key, "from": start.isoformat()} for key, start in amendments],
        "warnings": list(warnings or []),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True, help="the previous release tag, e.g. v15")
    ap.add_argument("--head", default="HEAD", help="the ref being released (default HEAD)")
    ap.add_argument("--tag", help="the tag being cut: check its CHANGELOG section")
    ap.add_argument(
        "--on",
        type=date.fromisoformat,
        help="the tag date. With --tag, the date in the tag's CHANGELOG heading; otherwise today in Australia/Brisbane",
    )
    ap.add_argument(
        "--commit-date",
        help="with --tag, the tag commit's ISO 8601 datetime (`git log -1 --format=%%cI <tag>`); the heading date must be "
        "its date in Australia/Brisbane. Default: the --head commit's",
    )
    ap.add_argument("--out", help="with --tag, write RELEASE.json here")
    args = ap.parse_args()

    changelog = _git("show", f"{args.head}:CHANGELOG.md").decode() if args.tag else ""
    if args.tag:
        problems = heading_errors(changelog, args.tag)
        for e in problems:
            print(f"error: {e}")
        if problems:
            return 1
    on = args.on or (args.tag and heading_date(changelog, args.tag)) or today_in_brisbane()
    commit_date = None
    if args.tag:
        try:
            commit_date = brisbane_date(args.commit_date or _git("log", "-1", "--format=%cI", args.head).decode().strip())
        except ValueError as exc:
            print(f"error: --commit-date: {exc}")
            return 1

    changes = classify(tree_at(args.base), tree_at(args.head), on)
    for (kind, reason), n in sorted(Counter((c.kind, c.reason) for c in changes).items()):
        print(f"{kind:<11} {n:>4}  {reason}")
    print(f"kinds: {', '.join(k for k in KINDS if k in computed_kinds(changes)) or 'none'}")
    warnings = late_amendments(changes, on)
    for w in warnings:
        print(f"::warning title=Late amendment::{w}" if os.environ.get("GITHUB_ACTIONS") == "true" else f"warning: {w}")

    if not args.tag:
        return 0
    errors = refusals(changes, changelog, args.tag, on, commit_date)
    for e in errors:
        print(f"error: {e}")
    if errors:
        return 1
    if args.out:
        Path(args.out).write_text(json.dumps(release_json(changes, changelog, args.tag, warnings), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
