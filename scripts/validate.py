#!/usr/bin/env python3
"""Every contract is checked; every $ref resolves; every one declares a version.

    python3 scripts/validate.py

Two tiers, because the registers that came from the Demiton monorepo are not
strictly-conformant JSON Schema, and never claimed to be:

  * `research/*.schema.json` (the disease-economics finding/source/protection
    registers) declare `$schema: .../draft/2020-12/schema` and mean it: checked
    with the real Draft202012Validator, `$ref`s and all.
  * `contracts/` and `history/` (tenant and platform registers) are JSON-Schema
    *shaped* - `type`, `properties`, `required` - but `type` is drawn from the
    monorepo's own closed field-type vocabulary (`decimal`, `money`, `currency`,
    `date`, `datetime`, `jurisdiction`, alongside the real JSON Schema primitives),
    not the JSON Schema spec's own `type` enum. Measured 2026-09-26: running the
    strict validator against them fails 562 of 656 documents on exactly this,
    and nothing in the monorepo itself validates them that strictly either -
    `shelf_schema_translate.py`'s own docstring calls this "D4, a closed
    field-type vocabulary. Anything it cannot express goes to the ledger, never
    coerced." So these are checked structurally: valid JSON, `properties` (where
    present) a dict of dicts, every field's `type` a known token (KNOWN_TYPES) -
    warned, not failed, if it's not, since the vocabulary can grow.

Contracts under `contracts/` and `research/` carry their version under one of two
keys, depending on where they came from: `x-schema-version` (research) or
`x-demiton-contract-version` (tenant/platform, SD024 decision 15). Unifying on one
key is a later decision (spec 09), not a rule this script enforces yet. Files
under `history/` are past versions, checked for validity only, not for carrying
the current highest version.

Exit code 1 on any error; warnings print but do not fail.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_KEYS = ("x-schema-version", "x-demiton-contract-version")
KNOWN_TYPES = {
    "null", "boolean", "object", "array", "number", "string", "integer",  # JSON Schema's own
    "decimal", "money", "currency", "date", "datetime", "jurisdiction",  # the monorepo's closed vocabulary
}


def research_schemas() -> list[Path]:
    return sorted((ROOT / "research").glob("*.schema.json"))


def shaped_contracts() -> list[Path]:
    return sorted((ROOT / "contracts").glob("*.schema.json")) + sorted((ROOT / "history").glob("*/*.schema.json"))


def _load(path: Path) -> tuple[dict | None, str | None]:
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


def _walk_field_types(node: object, path: str, warnings: list[str], rel: Path) -> None:
    if not isinstance(node, dict):
        return
    if "type" in node and isinstance(node["type"], str) and node["type"] not in KNOWN_TYPES:
        warnings.append(f"{rel}: {path}: type {node['type']!r} is not in the known vocabulary")
    for name, sub in (node.get("properties") or {}).items():
        _walk_field_types(sub, f"{path}/properties/{name}", warnings, rel)
    if isinstance(node.get("items"), dict):
        _walk_field_types(node["items"], f"{path}/items", warnings, rel)


def _check_version(path: Path, doc: dict, errors: list[str]) -> None:
    rel = path.relative_to(ROOT)
    present = [k for k in VERSION_KEYS if k in doc]
    if not present:
        errors.append(f"{rel}: no version key ({' or '.join(VERSION_KEYS)})")
        return
    if len(present) > 1:
        errors.append(f"{rel}: carries both {present[0]} and {present[1]} - only one is the source of truth")
        return
    version = str(doc[present[0]])
    if not SEMVER.match(version):
        errors.append(f"{rel}: {present[0]} must be MAJOR.MINOR.PATCH, got {version!r}")


def validate() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    research_docs: dict[str, dict] = {}
    for path in research_schemas():
        doc, parse_error = _load(path)
        rel = path.relative_to(ROOT)
        if parse_error:
            errors.append(f"{rel}: not valid JSON: {parse_error}")
            continue
        research_docs[str(path)] = doc

    resources = [
        (doc["$id"], Resource.from_contents(doc)) for doc in research_docs.values() if isinstance(doc.get("$id"), str)
    ]
    registry: Registry = Registry().with_resources(resources)  # type: ignore[assignment]

    for path_str, doc in research_docs.items():
        path, rel = Path(path_str), Path(path_str).relative_to(ROOT)
        try:
            Draft202012Validator.check_schema(doc)
            list(Draft202012Validator(doc, registry=registry).iter_errors({}))  # forces $ref resolution
        except Exception as exc:  # noqa: BLE001 - report every kind of schema error the same way
            errors.append(f"{rel}: {exc}")
            continue
        _check_version(path, doc, errors)

    for path in shaped_contracts():
        doc, parse_error = _load(path)
        rel = path.relative_to(ROOT)
        if parse_error:
            errors.append(f"{rel}: not valid JSON: {parse_error}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{rel}: not a JSON object")
            continue
        if "properties" in doc and not isinstance(doc["properties"], dict):
            errors.append(f"{rel}: 'properties' must be an object")
            continue
        _walk_field_types(doc, "#", warnings, rel)
        if "history" not in path.parts:  # a past version doesn't need to BE the current version
            _check_version(path, doc, errors)

    return errors, warnings


def main() -> int:
    errors, warnings = validate()
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    total = len(research_schemas()) + len(shaped_contracts())
    print(f"{len(errors)} error(s), {len(warnings)} warning(s), {total} document(s) checked")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
