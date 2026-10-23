#!/usr/bin/env python3
"""SM031 M4: flatten the obligation library to what a project reads.

    python3 scripts/resolve.py --count
    python3 scripts/resolve.py --flatten
    python3 scripts/resolve.py --out /tmp/flat

`obligations/_model/` holds abstract bases: one `model_law` base per document
adopted verbatim across jurisdictions (the model WHS Act), one `shared_shape`
base per duty whose wording is shared while the citation, clause and window are
not. A concrete in `obligations/<jurisdiction>/` either stands alone or carries
`extends: <base id>`, in which case its `obligations[]` are rows conforming to
`contracts/obligation_override.schema.json`. This script merges each concrete
with its base and emits the flattened instrument a project reads: no `extends`,
no `abstract`, no `_model/`, every row carrying its own key, duty, citation and
grade.

Two coverage rules, from SM031 decisions 5 and 10:

  * a `model_law` concrete must cover every base obligation, either with an
    override or with an explicit `removed: true` row. A silent drop is refused:
    it is the failure that reintroduces an unreviewed gap.
  * a `shared_shape` base is a catalogue, not a floor. A state that does not
    carry a listed duty simply does not override it, and nothing is emitted.

`validate.py` imports `tree_errors` from here, so the checks a tree must pass
and the flattening a tree produces can never drift apart.

Dated versions (SM052). A row may carry `in_force: {from, until, by, transitional}`,
and an instrument may carry one for all its rows; the resolver copies the
instrument's block onto each row that states none. Several rows of ONE instrument
may share a `key`: they are the versions of one duty. A version's id is its `from`
date, `original` when it has none. The resolver sorts them by `from` (none first) and
derives each earlier version's `until` and `by` from the next version's `from` and
`by`: `until` is the day before, so versions are contiguous by construction and an
author writes `until` only on the last version (a repeal). `by` names the date that
decides the version (vocab/selecting_dates.json). Where an earlier version's own
`by` differs from the next version's, the derived row carries `until_by` as well.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent

#: The fields a concrete override may supply (SM031 decision 4 as amended
#: 2026-09-30). `duty`, `consequence`, `protection_type`, `disease`, `severity`
#: and `evidence` are deliberately absent: a state that differs on those is a
#: new obligation under a new key (decision 5), not an override. `caveat` is
#: present because the states' caveats genuinely differ. `key` is not in this
#: list: it is the flattened row's own identity, always taken from the override.
OVERRIDABLE = (
    "citation",
    "clause",
    "window",
    "window_source_field",
    "threshold",
    "grade",
    "basis",
    "caveat",
    "in_force",
)

#: Overridable fields a concrete may set to `null` to clear an inherited value.
#: The one that forced this: New South Wales' Aboriginal-object notification duty
#: runs "within a reasonable time", so inheriting the base's 24-hour window would
#: misstate it. `citation` and `grade` are not here - a flattened row must carry
#: both.
CLEARABLE = ("window", "window_source_field", "threshold", "caveat", "basis")

#: Fields a concrete instrument states for itself; everything else is inherited.
#: `lang` is here because the concrete's words are its own: a base in one language
#: says nothing about the language a jurisdiction's text is read in.
#: `publisher` is here rather than inherited because a state's Act is published by
#: that state's parliament, not by whoever published the model law.
CONCRETE_HEADER = ("id", "lang", "title", "publisher", "jurisdictions", "citation", "in_force")
#: Fields a concrete instrument may inherit when it does not state them. `publisher`
#: is here as well as in CONCRETE_HEADER: a state's Act is published by that state's
#: parliament and states its own, while an approval-type instrument is published by
#: the regulator that issues it and inherits the base's publisher.
INHERITED_HEADER = ("source", "instrument_type", "publisher", "form")


class ResolveError(Exception):
    """A tree that cannot be flattened, with the reason named."""


def selecting_dates() -> tuple[str, ...]:
    """The dates an `in_force.by` may name: the keys of vocab/selecting_dates.json."""
    vocab = json.loads((ROOT / "vocab" / "selecting_dates.json").read_text())
    return tuple(k for k in vocab if not k.startswith("$"))


def as_date(value: object) -> date | None:
    """A date from a YAML date or an ISO `YYYY-MM-DD` string; None for None.
    Raises ValueError for anything else, so a caller can name the bad value."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValueError(f"{value!r} is not a date")


def _iso_block(block: object) -> object:
    if not isinstance(block, dict):
        return block
    return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in block.items()}


def iso_dates(doc: object) -> object:
    """`doc` with the dates in every `in_force` block (an unquoted `2027-07-01` loads as a
    date) as ISO strings, so a schema, a diff and `json.dumps` read them alike. The same
    object when nothing is dated, which is every document in the library today."""
    if not isinstance(doc, dict):
        return doc
    rows = doc.get("obligations") or []
    if "in_force" not in doc and not any(isinstance(o, dict) and "in_force" in o for o in rows):
        return doc
    out = dict(doc)
    if "in_force" in doc:
        out["in_force"] = _iso_block(doc["in_force"])
    out["obligations"] = [
        {**o, "in_force": _iso_block(o["in_force"])} if isinstance(o, dict) and "in_force" in o else o for o in rows
    ]
    return out


def _stamp_in_force(instrument: dict) -> dict:
    """Copy the instrument's `in_force` onto each of its rows that states none.

    A stamped row of a key with several versions is the original, never the last (the
    others date themselves), so the instrument's `until` is not copied onto it:
    `derive_versions` gives it the day before the next version's `from`, and the
    instrument's ceiling is held by the last version, which `validate.py` requires to
    state an `until` no later than the instrument's."""
    block = instrument.get("in_force")
    if not isinstance(block, dict):
        return instrument
    rows_in = instrument.get("obligations") or []
    count: dict[object, int] = {}
    for o in rows_in:
        count[o.get("key")] = count.get(o.get("key"), 0) + 1
    rows = []
    for o in rows_in:
        if "in_force" in o:
            rows.append(o)
        elif count[o.get("key")] > 1:
            rows.append({**o, "in_force": {k: v for k, v in block.items() if k != "until"}})
        else:
            rows.append({**o, "in_force": dict(block)})
    return {**instrument, "obligations": rows}


def abstract_in_force_errors(label: str, doc: dict) -> list[str]:
    """An abstract base is a catalogue of the shared wording, not a version of anything: a
    concrete's override inherits a base row's `in_force`, so a dated row there would bypass
    the concrete's own floor and ceiling (`validate.py`'s floor rule reads the concrete's
    block), and the resolver ignores a base's instrument-level block altogether. Dating
    belongs on the concrete instrument or its overriding rows."""
    if not doc.get("abstract"):
        return []
    errors: list[str] = []
    if doc.get("in_force") is not None:
        errors.append(
            f"{label}: abstract base {doc.get('id')} carries an instrument-level in_force, which the resolver "
            f"ignores (a concrete states its own); date the concrete instrument, not the base"
        )
    for row in doc.get("obligations") or []:
        if isinstance(row, dict) and row.get("in_force") is not None:
            errors.append(
                f"{label}: {row.get('key') or row.get('overrides')}: abstract base {doc.get('id')} carries a dated row "
                f"(in_force), which a concrete's override would inherit past the concrete's own floor and ceiling; "
                f"date the concrete's overriding row, not the base"
            )
    return errors


def base_files() -> list[Path]:
    return sorted(ROOT.glob("obligations/_model/**/*.yaml"))


def concrete_files() -> list[Path]:
    return sorted(p for p in ROOT.glob("obligations/*/*.yaml") if "_model" not in p.parts)


def load_doc(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def load_tree() -> tuple[list[dict], dict[str, tuple[dict, str]]]:
    """Every concrete document, plus every instrument (base or concrete) by id."""
    by_id: dict[str, tuple[dict, str]] = {}
    concretes: list[dict] = []
    for path in base_files() + concrete_files():
        doc = load_doc(path)
        rel = str(path.relative_to(ROOT))
        by_id[doc["id"]] = (doc, rel)
        if "_model" not in path.parts:
            concretes.append(doc)
    return concretes, by_id


def _extends_chain(start: str, by_id: dict[str, tuple[dict, str]]) -> list[str]:
    chain: list[str] = []
    cur: str | None = start
    while cur is not None:
        if cur in chain:
            chain.append(cur)
            return chain
        chain.append(cur)
        doc = by_id.get(cur, (None, ""))[0]
        cur = (doc or {}).get("extends")
        if cur is not None and cur not in by_id:
            chain.append(cur)
            return chain
    return chain


def _read_pairs() -> tuple[list[tuple[str, dict]], list[str]]:
    """Every base and concrete, with a file that will not parse reported rather
    than raised. `validate.py` reports the same parse error on its own pass; a
    tree check that raises cannot also say which file was broken."""
    pairs: list[tuple[str, dict]] = []
    errors: list[str] = []
    for path in base_files() + concrete_files():
        rel = str(path.relative_to(ROOT))
        try:
            pairs.append((rel, load_doc(path)))
        except yaml.YAMLError as exc:
            errors.append(f"{rel}: not valid YAML: {exc}")
    return pairs, errors


def tree_errors(docs: list[tuple[str, dict]] | None = None) -> list[str]:
    """Every check that needs more than one document: unique ids, resolvable and
    acyclic `extends`, a base that is abstract, overrides that name a real base
    obligation, no silent drop from a `model_law` base, and a resolved grade.

    `docs` is `[(label, document)]`. The real tree is read when it is omitted;
    the tests pass fixtures, so a two-file tree can be exercised without writing
    to `obligations/`."""
    if docs is None:
        pairs, parse_errors = _read_pairs()
    else:
        pairs, parse_errors = docs, []
    errors: list[str] = list(parse_errors)
    by_id: dict[str, tuple[dict, str]] = {}
    seen_ids: dict[str, str] = {}
    for rel, doc in pairs:
        iid = doc.get("id")
        if iid in seen_ids:
            errors.append(f"{rel}: instrument id {iid!r} duplicates {seen_ids[iid]} - `extends` resolves by id, so ids must be unique")
        else:
            seen_ids[iid] = rel
        by_id[iid] = (doc, rel)

    for doc, rel in by_id.values():
        errors.extend(abstract_in_force_errors(rel, doc))

    for doc, rel in by_id.values():
        if "extends" not in doc:
            continue
        target = doc["extends"]
        if target not in by_id:
            errors.append(f"{rel}: extends {target!r}, which is not the id of any instrument in this tree")
            continue
        base, base_rel = by_id[target]
        if not base.get("abstract"):
            errors.append(f"{rel}: extends {target!r} ({base_rel}), which is not abstract - only a base in obligations/_model/ may be extended")

    for iid, (doc, rel) in by_id.items():
        if "extends" not in doc:
            continue
        chain = _extends_chain(iid, by_id)
        if len(set(chain)) != len(chain):
            errors.append(f"{rel}: extends cycle: {' -> '.join(chain)}")

    for doc, rel in by_id.values():
        if "extends" not in doc or doc["extends"] not in by_id:
            continue
        base = by_id[doc["extends"]][0]
        base_keys = [o["key"] for o in base.get("obligations") or []]
        covered = {o.get("overrides") for o in doc.get("obligations") or []}
        for override in doc.get("obligations") or []:
            if override.get("overrides") not in base_keys:
                errors.append(
                    f"{rel}: obligation {override.get('key') or override.get('overrides')!r} overrides "
                    f"{override.get('overrides')!r}, which is not an obligation of base {doc['extends']!r}"
                )
        if base.get("model_type") == "model_law":
            for key in base_keys:
                if key not in covered:
                    errors.append(
                        f"{rel}: base obligation {key!r} of {doc['extends']!r} is neither overridden nor "
                        f"`removed: true` - a model_law concrete may not silently drop it (decision 10)"
                    )
        for override in doc.get("obligations") or []:
            if override.get("removed"):
                continue
            inherited = next((o for o in base.get("obligations") or [] if o["key"] == override.get("overrides")), {})
            if not (override.get("grade") or inherited.get("grade")):
                errors.append(
                    f"{rel}: obligation {override.get('key')!r} resolves with no grade - the base leaves it to the "
                    f"concrete that first reads this jurisdiction's text, so the concrete must supply one"
                )
    duty_shapes = json.loads((ROOT / "vocab" / "duty_shapes.json").read_text())
    # SM037 (Demiton, Delegation of Authority): every resolved row says what kind
    # of sign-off its evidence needs. An override cannot set approval_class (its
    # schema refuses the field), so checking every base and standalone row is
    # checking every resolved row.
    for doc, rel in by_id.values():
        if "extends" in doc:
            continue
        for ob in doc.get("obligations") or []:
            if not ob.get("approval_class"):
                errors.append(
                    f"{rel}: obligation {ob.get('key')!r} has no approval_class - every row names one of "
                    f"vocab/approval_classes.json, so an approval can be routed (SM037)"
                )
            # The same reasoning for duty_shape: an override cannot set it, so a
            # base or standalone row without one leaves a resolved row without one.
            shape = ob.get("duty_shape")
            if not shape:
                errors.append(
                    f"{rel}: obligation {ob.get('key')!r} has no duty_shape - every row names the duty it "
                    f"states, a key of vocab/duty_shapes.json, so it reads beside the same duty elsewhere"
                )
            elif shape not in duty_shapes:
                errors.append(f"{rel}: obligation {ob.get('key')!r}: duty_shape {shape!r} is not in vocab/duty_shapes.json")
    errors.extend(version_errors(_resolved_concretes(by_id)))
    return errors


def _resolved_concretes(by_id: dict[str, tuple[dict, str]]) -> list[tuple[str, dict]]:
    """Every concrete instrument as `resolve_instrument` flattens it, for the checks that
    compare rows. A concrete that cannot flatten has its reason reported by the checks
    above, so it is skipped here rather than reported twice."""
    resolved: list[tuple[str, dict]] = []
    for doc, rel in by_id.values():
        if doc.get("abstract"):
            continue
        try:
            resolved.append((rel, resolve_instrument(doc, by_id)))
        except (ResolveError, KeyError, TypeError, AttributeError):
            continue
    return resolved


#: The fields every version of one key shares (SM052 decision 10). A change to any of
#: them changes which engine runs, which disease the catch is booked to, what evidences
#: it, or which card it reads under, so it is a new key.
VERSION_SHARED = ("protection_type", "disease", "evidence.register", "duty_shape")


def _shared_value(row: dict, field: str) -> object:
    if field == "evidence.register":
        return (row.get("evidence") or {}).get("register")
    return row.get(field)


def version_errors(instruments: list[tuple[str, dict]]) -> list[str]:
    """The checks on the versions of one key (SM052 decisions 9 and 10), on instruments
    already resolved. A key repeats only within one instrument (`validate.py` refuses it
    across two). Within one: `(key, from)` is unique, only the last version states an
    `until` (the resolver derives the rest, so a stated one is an overlap, a gap, or a
    copy of what it would derive), and versions share `protection_type`, `disease`,
    `evidence.register` and `duty_shape`. Every message names the key."""
    errors: list[str] = []
    for label, inst in instruments:
        groups: dict[str, list[dict]] = {}
        for row in inst.get("obligations") or []:
            if isinstance(row, dict) and row.get("key"):
                groups.setdefault(row["key"], []).append(row)
        for key, rows in groups.items():
            if len(rows) < 2:
                continue
            parsed: list[tuple[dict, date | None, date | None]] = []
            for row in rows:
                block = row.get("in_force") if isinstance(row.get("in_force"), dict) else {}
                try:
                    parsed.append((row, as_date(block.get("from")), as_date(block.get("until"))))
                except ValueError as exc:
                    errors.append(f"{label}: {key}: in_force has a date that is not YYYY-MM-DD ({exc})")
            if len(parsed) != len(rows):
                continue
            by_start: dict[date | None, int] = {}
            for _, start, _ in parsed:
                by_start[start] = by_start.get(start, 0) + 1
            for start, n in by_start.items():
                if n > 1:
                    which = f"from {start.isoformat()}" if start else "no `from` (the original)"
                    errors.append(
                        f"{label}: {key}: {n} versions have {which} - (key, from) must be unique, "
                        f"so give each version of a key its own `from`"
                    )
            if any(n > 1 for n in by_start.values()):
                continue
            ordered = sorted(parsed, key=lambda p: p[1] or date.min)
            for (row, start, until), (_, next_start, _) in zip(ordered, ordered[1:]):
                if until is None:
                    continue
                vid = start.isoformat() if start else "original"
                derived = (next_start - timedelta(days=1)).isoformat()
                if until >= next_start:
                    errors.append(
                        f"{label}: {key}: version {vid} states until {until.isoformat()}, which overlaps the version "
                        f"from {next_start.isoformat()}; remove it, resolve.py derives {derived}"
                    )
                elif until < next_start - timedelta(days=1):
                    errors.append(
                        f"{label}: {key}: version {vid} states until {until.isoformat()} but the next version starts "
                        f"{next_start.isoformat()}, a gap in which no version is in force; remove it, resolve.py derives {derived}"
                    )
                else:
                    errors.append(
                        f"{label}: {key}: version {vid} states until {until.isoformat()}; only the last version of a "
                        f"key may, because resolve.py derives it from the next version's `from`"
                    )
            first = ordered[0][0]
            for row, start, _ in ordered[1:]:
                for field in VERSION_SHARED:
                    a, b = _shared_value(first, field), _shared_value(row, field)
                    if a != b:
                        errors.append(
                            f"{label}: {key}: the version from {start.isoformat() if start else 'original'} changes {field} "
                            f"from {a!r} to {b!r}; versions of one key share protection_type, disease, evidence.register "
                            f"and duty_shape, so a change to any of them is a new key"
                        )
    return errors


def resolve_instrument(doc: dict, by_id: dict[str, tuple[dict, str]]) -> dict:
    """One concrete flattened against its base, or unchanged if it extends nothing.

    An instrument's `in_force` is copied onto each row that states none. Versions of a
    key are not derived here (`derive_versions` does that); an extending concrete may
    carry several overrides of one base key, each with its own `in_force`."""
    doc = iso_dates(doc)
    if "extends" not in doc:
        return _stamp_in_force(doc)

    base = iso_dates(by_id[doc["extends"]][0])
    out: dict[str, Any] = {f: base[f] for f in INHERITED_HEADER if f in base}
    out.update({f: doc[f] for f in CONCRETE_HEADER if f in doc})
    out["id"] = doc["id"]

    overrides: dict[str, list[dict]] = {}
    for o in doc.get("obligations") or []:
        if "overrides" in o:
            overrides.setdefault(o["overrides"], []).append(o)
    rows: list[dict] = []
    for base_row in base.get("obligations") or []:
        group = overrides.get(base_row["key"])
        if not group:
            if base.get("model_type") == "shared_shape":
                continue
            raise ResolveError(
                f"{doc['id']}: base obligation {base_row['key']!r} is neither overridden nor `removed: true`"
            )
        for override in group:
            if override.get("removed"):
                continue
            row = dict(base_row)
            for field in OVERRIDABLE:
                if field not in override:
                    continue
                if override[field] is None and field in CLEARABLE:
                    row.pop(field, None)
                else:
                    row[field] = override[field]
            row["key"] = override["key"]
            if row.get("grade") != "demiton_default":
                row.pop("basis", None)
            if not row.get("grade"):
                raise ResolveError(
                    f"{doc['id']}: {row['key']!r} resolves with no grade - the concrete must supply one"
                )
            rows.append(row)
    out["obligations"] = rows
    return _stamp_in_force(out)


def derive_versions(instrument: dict) -> dict:
    """Give each earlier version of a repeated key the `until` (the day before the next
    version's `from`) and the `by` (the next version's) that the author did not write.

    Rows keep their authored order. A key with one row is untouched. Run on a tree that
    `tree_errors` accepts: with two undated rows of a key, or a next version with no
    `from`, there is nothing to derive from and the rows are left as they are."""
    rows = instrument["obligations"]
    groups: dict[str, list[int]] = {}
    for i, row in enumerate(rows):
        groups.setdefault(row["key"], []).append(i)
    out = list(rows)
    for indexes in groups.values():
        if len(indexes) < 2:
            continue
        start = lambda i: as_date((rows[i].get("in_force") or {}).get("from"))  # noqa: E731
        ordered = sorted(indexes, key=lambda i: start(i) or date.min)
        for i, j in zip(ordered, ordered[1:]):
            next_start = start(j)
            if next_start is None or next_start == start(i):
                continue
            block = dict(rows[i].get("in_force") or {})
            next_by = (rows[j].get("in_force") or {}).get("by")
            block["until"] = (next_start - timedelta(days=1)).isoformat()
            block.pop("until_by", None)
            if "by" not in block:
                block["by"] = next_by
            elif block["by"] != next_by:
                block["until_by"] = next_by
            out[i] = {**rows[i], "in_force": block}
    return {**instrument, "obligations": out}


def flatten_tree(concretes: list[dict], by_id: dict[str, tuple[dict, str]]) -> list[dict]:
    return [derive_versions(resolve_instrument(doc, by_id)) for doc in concretes]


def flatten_docs(docs: list[tuple[str, dict]]) -> list[dict]:
    """`flatten()` over `[(label, document)]` instead of the files on disk, so a test can
    flatten a fixture tree. Abstract bases are read, never emitted."""
    by_id = {doc["id"]: (doc, label) for label, doc in docs}
    return flatten_tree([doc for _, doc in docs if not doc.get("abstract")], by_id)


def flatten() -> list[dict]:
    concretes, by_id = load_tree()
    return flatten_tree(concretes, by_id)


def count() -> int:
    return sum(len(instrument["obligations"]) for instrument in flatten())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--count", action="store_true", help="print the flattened obligation count")
    ap.add_argument("--flatten", action="store_true", help="print the flattened instruments as JSON")
    ap.add_argument("--out", metavar="DIR", help="write one flattened YAML file per concrete instrument")
    args = ap.parse_args()

    errors = tree_errors()
    if errors:
        for e in errors:
            print(f"error: {e}")
        return 1

    if args.out:
        out = Path(args.out)
        for instrument in flatten():
            # One directory per jurisdiction, mirroring the library itself, so a
            # consumer's `obligations/<JURISDICTION>/*.yaml` reader works against
            # the released asset unchanged. A country-wide instrument lands under
            # its country code, which is also where the library files it.
            jurisdiction = (instrument.get("jurisdictions") or ["AU"])[0]
            target = out / jurisdiction
            target.mkdir(parents=True, exist_ok=True)
            (target / f"{instrument['id']}.yaml").write_text(
                yaml.safe_dump(instrument, sort_keys=False, allow_unicode=True, width=100)
            )
        print(f"{len(flatten())} instruments, {count()} obligations -> {out}")
        return 0

    if args.flatten:
        print(json.dumps(flatten(), indent=2, ensure_ascii=False))
        return 0

    print(count())
    return 0


if __name__ == "__main__":
    sys.exit(main())
