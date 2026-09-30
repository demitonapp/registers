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
"""
from __future__ import annotations

import argparse
import json
import sys
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
)

#: Overridable fields a concrete may set to `null` to clear an inherited value.
#: The one that forced this: New South Wales' Aboriginal-object notification duty
#: runs "within a reasonable time", so inheriting the base's 24-hour window would
#: misstate it. `citation` and `grade` are not here - a flattened row must carry
#: both.
CLEARABLE = ("window", "window_source_field", "threshold", "caveat", "basis")

#: Fields a concrete instrument states for itself; everything else is inherited.
#: `publisher` is here rather than inherited because a state's Act is published by
#: that state's parliament, not by whoever published the model law.
CONCRETE_HEADER = ("id", "title", "publisher", "jurisdictions", "citation")
#: Fields a concrete instrument may inherit when it does not state them. `publisher`
#: is here as well as in CONCRETE_HEADER: a state's Act is published by that state's
#: parliament and states its own, while an approval-type instrument is published by
#: the regulator that issues it and inherits the base's publisher.
INHERITED_HEADER = ("source", "instrument_type", "publisher", "form")


class ResolveError(Exception):
    """A tree that cannot be flattened, with the reason named."""


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
    return errors


def resolve_instrument(doc: dict, by_id: dict[str, tuple[dict, str]]) -> dict:
    """One concrete flattened against its base, or unchanged if it extends nothing."""
    if "extends" not in doc:
        return doc

    base = by_id[doc["extends"]][0]
    out: dict[str, Any] = {f: base[f] for f in INHERITED_HEADER if f in base}
    out.update({f: doc[f] for f in CONCRETE_HEADER if f in doc})
    out["id"] = doc["id"]

    overrides = {o["overrides"]: o for o in doc.get("obligations") or [] if "overrides" in o}
    rows: list[dict] = []
    for base_row in base.get("obligations") or []:
        override = overrides.get(base_row["key"])
        if override is None:
            if base.get("model_type") == "shared_shape":
                continue
            raise ResolveError(
                f"{doc['id']}: base obligation {base_row['key']!r} is neither overridden nor `removed: true`"
            )
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
    return out


def flatten() -> list[dict]:
    concretes, by_id = load_tree()
    return [resolve_instrument(doc, by_id) for doc in concretes]


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
