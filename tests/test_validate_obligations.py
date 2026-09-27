"""SM030 O1 Acceptance: the obligation-library validator refuses what it must
refuse and passes what it must pass.

    python -m pytest tests/test_validate_obligations.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate import validate_instrument_doc  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "obligations"


def _load(path: Path) -> object:
    return yaml.safe_load(path.read_text())


def test_valid_fixture_passes() -> None:
    doc = _load(FIXTURES / "valid" / "example.yaml")
    assert validate_instrument_doc(doc, "valid/example.yaml") == []


def test_row_without_primary_citation_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "no_citation.yaml")
    errors = validate_instrument_doc(doc, "invalid/no_citation.yaml")
    assert errors, "an obligation with no citation must be refused"
    assert any("citation" in e for e in errors)


def test_unknown_jurisdiction_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "unknown_jurisdiction.yaml")
    errors = validate_instrument_doc(doc, "invalid/unknown_jurisdiction.yaml")
    assert errors, "an unknown jurisdiction code must be refused"
    assert any("jurisdictions.json" in e for e in errors)


def test_protection_type_outside_the_four_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "bad_protection_type.yaml")
    errors = validate_instrument_doc(doc, "invalid/bad_protection_type.yaml")
    assert errors, "a protection_type outside the four must be refused"
    assert any("protection_type" in e for e in errors)


def test_threshold_obligation_without_its_threshold_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "threshold_without_direction.yaml")
    errors = validate_instrument_doc(doc, "invalid/threshold_without_direction.yaml")
    assert any("must say its threshold" in e for e in errors)


def test_threshold_direction_outside_max_and_min_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "threshold_without_direction.yaml")
    doc["obligations"][0]["threshold"] = {"direction": "lowest", "set_by": "library"}
    errors = validate_instrument_doc(doc, "fixture")
    assert any("direction" in e or "lowest" in e for e in errors)
