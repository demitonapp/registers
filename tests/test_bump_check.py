"""bump_check: a requirement added under `allOf`/`then`/`else` binds the same
document as its parent, so it is MAJOR when that parent already existed.

    python -m pytest tests/test_bump_check.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from bump_check import schema_bump_needed  # noqa: E402

OLD = {
    "type": "object",
    "required": ["id"],
    "properties": {"id": {"type": "string"}},
}


def _with(**extra) -> dict:
    return {**OLD, "properties": {**OLD["properties"], "kind": {"type": "string"}, "state": {"type": "string"}}, **extra}


def test_a_conditional_requirement_on_an_existing_document_is_major():
    # `{"id": "x", "kind": "photo"}` validated before (no additionalProperties)
    # and fails after, because `state` is now required alongside `kind`.
    new = _with(allOf=[{"if": {"required": ["kind"]}, "then": {"required": ["state"]}}])
    assert schema_bump_needed(OLD, new) == "major"


def test_an_else_requirement_is_major_too():
    new = _with(allOf=[{"if": {"required": ["kind"]}, "else": {"required": ["state"]}}])
    assert schema_bump_needed(OLD, new) == "major"


def test_a_lone_if_constrains_nothing():
    new = _with(allOf=[{"if": {"required": ["kind"]}, "then": True}])
    assert schema_bump_needed(OLD, new) == "minor"


def test_a_required_list_inside_a_new_property_is_still_minor():
    # The 2026-09-26 rule this must not undo: the whole property is new.
    new = {**OLD, "properties": {**OLD["properties"], "site": {
        "type": "object", "required": ["lat"], "properties": {"lat": {"type": "number"}},
    }}}
    assert schema_bump_needed(OLD, new) == "minor"


def test_a_new_top_level_requirement_is_major():
    new = {**_with(), "required": ["id", "kind"]}
    assert schema_bump_needed(OLD, new) == "major"
