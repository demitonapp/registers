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
import resolve  # noqa: E402

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


# --- SM031 M1: the inheritance schema fields -------------------------------


def test_abstract_base_and_extending_concrete_pass() -> None:
    """The two valid shapes SM031 adds: a base in obligations/_model/ with no
    jurisdiction and no grade, and the concrete that extends it."""
    assert validate_instrument_doc(_load(FIXTURES / "valid" / "abstract_base.yaml"), "base") == []
    assert validate_instrument_doc(_load(FIXTURES / "valid" / "extending_concrete.yaml"), "concrete") == []


def test_extends_resolves_to_abstract_base() -> None:
    """`extends` resolves to an instrument id, and that instrument must be a base.
    A concrete extending a non-abstract instrument is refused by the tree check."""
    base = _load(FIXTURES / "valid" / "abstract_base.yaml")
    concrete = _load(FIXTURES / "valid" / "extending_concrete.yaml")
    assert resolve.tree_errors([("base.yaml", base), ("concrete.yaml", concrete)]) == []

    points_at_concrete = dict(concrete, extends="fixture_state_act")
    errors = resolve.tree_errors([("base.yaml", base), ("concrete.yaml", points_at_concrete)])
    assert any("not abstract" in e for e in errors), errors

    missing = _load(FIXTURES / "invalid" / "extends_missing_base.yaml")
    errors = resolve.tree_errors([("invalid/extends_missing_base.yaml", missing)])
    assert any("not the id of any instrument" in e for e in errors), errors


def test_non_abstract_requires_jurisdiction() -> None:
    """A concrete names where it applies; a base names no place."""
    errors = validate_instrument_doc(_load(FIXTURES / "invalid" / "non_abstract_empty_jurisdictions.yaml"), "concrete")
    assert any("jurisdictions" in e for e in errors), errors

    errors = validate_instrument_doc(_load(FIXTURES / "invalid" / "abstract_with_jurisdiction.yaml"), "base")
    assert any("jurisdictions" in e for e in errors), errors


def test_model_type_requires_abstract() -> None:
    """`model_type` says which tier a base is, so a concrete carrying one is
    refused, and an abstract instrument without one is refused too."""
    errors = validate_instrument_doc(_load(FIXTURES / "invalid" / "model_type_on_concrete.yaml"), "concrete")
    assert any("model_type" in e for e in errors), errors

    base = _load(FIXTURES / "valid" / "abstract_base.yaml")
    base.pop("model_type")
    errors = validate_instrument_doc(base, "base")
    assert any("model_type" in e for e in errors), errors


def test_shared_shape_bases_are_abstract() -> None:
    """SM031 M3: every base under obligations/_model/ is abstract and carries the
    model_type that says which tier it is. M3 authors the four shared-shape
    families; M2 authors the model-law pair."""
    bases = resolve.base_files()
    assert bases, "obligations/_model/ holds the bases"
    for path in bases:
        doc = _load(path)
        assert doc.get("abstract") is True, path
        assert doc.get("model_type") in ("model_law", "shared_shape"), path
        assert doc.get("jurisdictions") == [], path
        assert doc["model_type"].replace("_", "-") in path.parts, f"{path} is not filed under its model_type"
